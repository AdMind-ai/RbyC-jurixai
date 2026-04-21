from django.contrib import admin

from billing.models import BillingAccount, BillingInvoice, ProviderMonthlyCost


@admin.register(BillingAccount)
class BillingAccountAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "stripe_customer_id",
        "payment_method_ready",
        "card_brand",
        "card_last4",
        "card_exp_month",
        "card_exp_year",
        "updated_at",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(BillingInvoice)
class BillingInvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "period_month",
        "amount_eur",
        "currency",
        "status",
        "stripe_invoice_id",
        "attempt_count",
        "paid_at",
        "last_attempt_at",
    )
    list_filter = ("status", "currency", "created_by_task")
    search_fields = ("stripe_invoice_id", "stripe_payment_intent_id")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "period_month"


@admin.register(ProviderMonthlyCost)
class ProviderMonthlyCostAdmin(admin.ModelAdmin):
    list_display = (
        "provider",
        "period_month",
        "provider_amount",
        "amount_with_markup",
        "total_with_vat",
        "amount",
        "currency",
        "source",
        "external_project_id",
        "fetched_at",
    )
    list_filter = ("provider", "source", "currency")
    search_fields = ("provider", "external_project_id")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "period_month"
