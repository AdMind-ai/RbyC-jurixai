import logging

from celery import shared_task

from billing.services.monthly_billing import MonthlyBillingService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60 * 30)
def generate_monthly_billing_invoice(self, month=None):
    try:
        result = MonthlyBillingService.generate_invoice_for_month(
            month=month,
            created_by_task=True,
        )
        status = str(result.invoice.status)
        logger.info(
            "Monthly billing invoice task completed",
            extra={
                "invoice_id": result.invoice.id,
                "period_month": result.invoice.period_month.strftime("%Y-%m"),
                "status": status,
                "charged": result.charged,
                "total_usage_cost": str(result.total_usage_cost),
            },
        )
        return {
            "invoice_id": result.invoice.id,
            "period_month": result.invoice.period_month.strftime("%Y-%m"),
            "status": status,
            "charged": result.charged,
            "total_usage_cost": str(result.total_usage_cost),
        }
    except Exception as exc:
        logger.exception("Monthly billing invoice task failed")
        raise self.retry(exc=exc)
