# core/tasks.py
import logging
from datetime import date, timedelta

from django.conf import settings
from celery import shared_task

from core.services.vera_cost_sync_service import VeraCostSyncService

logger = logging.getLogger(__name__)


@shared_task
def test_task(word):
    print(f"Executando funcao {word}!")
    return True


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
