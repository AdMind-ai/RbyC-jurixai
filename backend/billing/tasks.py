import logging
from datetime import date

from celery import shared_task

from billing.services.monthly_billing import MonthlyBillingService
from billing.services.provider_costs import ProviderCostService

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


@shared_task(bind=True, max_retries=3, default_retry_delay=60 * 30)
def sync_openai_rbyc_cost(self, month=None):
    try:
        period_month = date.fromisoformat(month).replace(day=1) if month else date.today().replace(day=1)
        cost = ProviderCostService.refresh_openai_cost(period_month)
        logger.info(
            "OpenAI RbyC cost sync task completed",
            extra={
                "period_month": period_month.strftime("%Y-%m"),
                "provider_amount": str(cost.provider_amount),
                "currency": cost.currency,
                "source": cost.source,
                "external_project_id": cost.external_project_id,
            },
        )
        return {
            "period_month": period_month.strftime("%Y-%m"),
            "provider_amount": str(cost.provider_amount),
            "currency": cost.currency,
            "source": cost.source,
            "external_project_id": cost.external_project_id,
        }
    except Exception as exc:
        logger.exception("OpenAI RbyC cost sync task failed")
        raise self.retry(exc=exc)
