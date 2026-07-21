# core/tasks.py
import logging
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from celery import shared_task

from core.services.vera_cost_sync_service import VeraCostSyncService

logger = logging.getLogger(__name__)


@shared_task
def test_task(word):
    print(f"Executando funcao {word}!")
    return True


# ─── Notification tasks ───────────────────────────────────────────────────────

@shared_task
def notify_monthly_consumption_report():
    """
    Giorno 1 di ogni mese: crea notifica per il report mensile disponibile.
    """
    from core.models.notification_model import Notification, NotificationType
    import calendar

    today = date.today()
    # Il report è relativo al mese precedente
    first_day = today.replace(day=1)
    prev_month_last = first_day - timedelta(days=1)
    month_name = prev_month_last.strftime("%B %Y")

    # Evita duplicati: non creare se esiste già per questo mese
    already_exists = Notification.objects.filter(
        notification_type=NotificationType.CONSUMPTION_REPORT,
        created_at__year=today.year,
        created_at__month=today.month,
    ).exists()
    if already_exists:
        logger.info("notify_monthly_consumption_report: notifica già creata per %s", today)
        return {"status": "already_exists"}

    Notification.objects.create(
        notification_type=NotificationType.CONSUMPTION_REPORT,
        title=f"Report consumo AI di {month_name} disponibile",
        body=f"Il report dei costi AI per il mese di {month_name} è disponibile nella sezione Consumo AI → Utilizzo.",
        reference_type="usage_report",
    )
    logger.info("notify_monthly_consumption_report: creata notifica per %s", month_name)
    return {"status": "created", "month": month_name}


@shared_task
def notify_low_wallet_balance():
    """
    Controllo giornaliero: se il saldo wallet è sotto il threshold, crea notifica.
    Evita duplicati: non crea se già presente nelle ultime 24 ore.
    """
    from core.models.notification_model import Notification, NotificationType
    from django.utils import timezone

    try:
        from billing.services.wallet import WalletService
        wallet_status = WalletService.build_status()
    except Exception as exc:
        logger.warning("notify_low_wallet_balance: impossibile leggere wallet: %s", exc)
        return {"status": "error", "detail": str(exc)}

    balance = wallet_status.get("balanceEur", 0)
    threshold = wallet_status.get("thresholdEur", 0)
    needs_recharge = wallet_status.get("needsRecharge", False)

    if not needs_recharge:
        return {"status": "ok", "balance": balance}

    # Evita duplicati nelle ultime 24 ore
    cutoff = timezone.now() - timedelta(hours=24)
    already_exists = Notification.objects.filter(
        notification_type=NotificationType.CONSUMPTION_LOW_BALANCE,
        created_at__gte=cutoff,
    ).exists()
    if already_exists:
        return {"status": "already_notified"}

    Notification.objects.create(
        notification_type=NotificationType.CONSUMPTION_LOW_BALANCE,
        title=f"Saldo wallet basso — €{balance:.2f} disponibili",
        body=f"Il saldo del wallet è sceso sotto la soglia di €{threshold:.2f}. Ricarica per continuare a usare i servizi AI.",
        reference_type="wallet",
    )
    logger.info("notify_low_wallet_balance: notifica creata, saldo=€%s", balance)
    return {"status": "created", "balance": balance}


@shared_task
def notify_wallet_credit_usage_thresholds():
    """
    Controllo giornaliero: notifica quando il credito wallet raggiunge
    soglie di utilizzo del 20%, 40%, 60%, 80% e 95%.
    """
    from core.models.notification_model import Notification, NotificationType

    try:
        from billing.models import WalletTransaction, WalletTransactionStatus
        from billing.services.wallet import WalletService

        wallet_status = WalletService.build_status()
        latest_credit = (
            WalletTransaction.objects.filter(
                amount_eur__gt=0,
                status=WalletTransactionStatus.COMPLETED,
            )
            .order_by("-created_at", "-id")
            .first()
        )
    except Exception as exc:
        logger.warning("notify_wallet_credit_usage_thresholds: impossibile leggere wallet: %s", exc)
        return {"status": "error", "detail": str(exc)}

    if not latest_credit:
        return {"status": "no_credit_cycle"}

    credit_amount = Decimal(str(latest_credit.amount_eur))
    if credit_amount <= Decimal("0.00"):
        return {"status": "no_credit_cycle"}

    balance = Decimal(str(wallet_status.get("balanceEur") or 0)).quantize(Decimal("0.01"))
    used_amount = credit_amount - balance
    if used_amount <= Decimal("0.00"):
        return {
            "status": "below_threshold",
            "usage_percentage": 0,
            "balance": float(balance),
        }

    usage_percentage = (used_amount / credit_amount * Decimal("100")).quantize(Decimal("0.01"))

    for threshold_pct in [95, 80, 60, 40, 20]:
        label = f"{threshold_pct}%"
        if usage_percentage < Decimal(str(threshold_pct)):
            continue

        reference_id = f"{latest_credit.id}:{threshold_pct}"
        already_exists = Notification.objects.filter(
            notification_type=NotificationType.CONSUMPTION_THRESHOLD,
            reference_type="wallet_credit_usage",
            reference_id=reference_id,
        ).exists()
        if already_exists:
            return {
                "status": "already_notified",
                "threshold": threshold_pct,
                "usage_percentage": float(usage_percentage),
                "balance": float(balance),
                "credit_amount": float(credit_amount),
            }

        if threshold_pct == 95:
            title = "Credito wallet quasi esaurito"
        else:
            title = f"Credito wallet utilizzato al {label}"
        body = (
            f"Hai utilizzato almeno il {label} del credito wallet. "
            f"Saldo disponibile: EUR {balance:.2f} su EUR {credit_amount:.2f}."
        )

        Notification.objects.create(
            notification_type=NotificationType.CONSUMPTION_THRESHOLD,
            title=title,
            body=body,
            reference_type="wallet_credit_usage",
            reference_id=reference_id,
        )
        logger.info(
            "notify_wallet_credit_usage_thresholds: notifica %s creata (balance=EUR %s, credit=EUR %s)",
            label,
            balance,
            credit_amount,
        )
        return {
            "status": "created",
            "threshold": threshold_pct,
            "usage_percentage": float(usage_percentage),
            "balance": float(balance),
            "credit_amount": float(credit_amount),
        }

    return {
        "status": "below_threshold",
        "usage_percentage": float(usage_percentage),
        "balance": float(balance),
        "credit_amount": float(credit_amount),
    }


@shared_task
def notify_monthly_spend_threshold():
    return notify_wallet_credit_usage_thresholds()

@shared_task(bind=True, max_retries=3, default_retry_delay=60 * 30)
def sync_vera_costs(self, days=None, provider="all"):
    try:
        provider = (provider or "all").lower()
        if provider not in {"all", "openai", "anthropic"}:
            raise ValueError("provider must be one of: all, openai, anthropic")

        sync_days = int(days or getattr(settings, "VERA_COST_SYNC_DAYS", 35))
        sync_days = max(1, min(sync_days, 366))
        end_date = date.today()
        start_date = end_date - timedelta(days=sync_days - 1)
        if provider == "all":
            result = VeraCostSyncService.sync_range(start_date, end_date)
        elif provider == "openai":
            result = {"openai": VeraCostSyncService._sync_openai_range(start_date, end_date)}
        else:
            result = {
                "anthropic": VeraCostSyncService._sync_anthropic_range(start_date, end_date)
            }

        logger.info(
            "Vera costs sync task completed",
            extra={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": sync_days,
                "provider": provider,
            },
        )
        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": sync_days,
            "provider": provider,
            "result": result,
        }
    except Exception as exc:
        logger.exception("Vera costs sync task failed")
        raise self.retry(exc=exc)


