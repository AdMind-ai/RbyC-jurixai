from django.urls import path

from billing.views import (
    BillingMonthlySummaryView,
    BillingSetupSessionView,
    BillingStatusView,
    StripeWebhookView,
)

urlpatterns = [
    path("status/", BillingStatusView.as_view(), name="billing-status"),
    path("monthly-summary/", BillingMonthlySummaryView.as_view(), name="billing-monthly-summary"),
    path("setup-session/", BillingSetupSessionView.as_view(), name="billing-setup-session"),
    path("webhook/", StripeWebhookView.as_view(), name="stripe-webhook"),
]
