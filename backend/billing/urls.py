from django.urls import path

from billing.views import (
    BillingMonthlySummaryView,
    BillingSetupSessionView,
    BillingStatusView,
    StripeWebhookView,
    WalletAdminAdjustmentView,
    WalletRechargeView,
    WalletStatusView,
    WalletTransactionListView,
)

urlpatterns = [
    path("status/", BillingStatusView.as_view(), name="billing-status"),
    path("monthly-summary/", BillingMonthlySummaryView.as_view(), name="billing-monthly-summary"),
    path("setup-session/", BillingSetupSessionView.as_view(), name="billing-setup-session"),
    path("wallet/", WalletStatusView.as_view(), name="billing-wallet"),
    path("wallet/transactions/", WalletTransactionListView.as_view(), name="billing-wallet-transactions"),
    path("wallet/recharge/", WalletRechargeView.as_view(), name="billing-wallet-recharge"),
    path("wallet/admin-adjustment/", WalletAdminAdjustmentView.as_view(), name="billing-wallet-admin-adjustment"),
    path("webhook/", StripeWebhookView.as_view(), name="stripe-webhook"),
]
