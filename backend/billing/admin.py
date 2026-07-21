from django.contrib import admin

from billing.models import (
    BillingAccount,
    BillingInvoice,
    ProviderMonthlyCost,
    ProviderUsageCost,
    Wallet,
    WalletTransaction,
)


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


class WalletTransactionInline(admin.TabularInline):
    model = WalletTransaction
    extra = 0
    readonly_fields = (
        "transaction_type",
        "status",
        "amount_eur",
        "balance_after_eur",
        "description",
        "stripe_payment_intent_id",
        "created_at",
    )
    can_delete = False
    ordering = ("-created_at",)


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "billing_account",
        "balance_eur",
        "currency",
        "auto_recharge_enabled",
        "recharge_amount_eur",
        "threshold_eur",
        "last_recharge_attempt_at",
        "updated_at",
    )
    list_filter = ("auto_recharge_enabled", "currency")
    readonly_fields = ("created_at", "updated_at")
    inlines = [WalletTransactionInline]


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "transaction_type",
        "status",
        "amount_eur",
        "balance_after_eur",
        "description",
        "stripe_payment_intent_id",
    )
    list_filter = ("transaction_type", "status", "created_at")
    search_fields = (
        "description",
        "idempotency_key",
        "stripe_payment_intent_id",
        "stripe_invoice_id",
    )
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"


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


@admin.register(ProviderUsageCost)
class ProviderUsageCostAdmin(admin.ModelAdmin):
    list_display = (
        "provider",
        "external_request_id",
        "amount",
        "currency",
        "provider_currency",
        "usage_record",
        "occurred_at",
    )
    list_filter = ("provider", "currency", "provider_currency")
    search_fields = ("provider", "external_request_id")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "occurred_at"
