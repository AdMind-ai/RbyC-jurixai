from __future__ import annotations

from rest_framework import serializers


class BillingCardSerializer(serializers.Serializer):
    brand = serializers.CharField(allow_blank=True, allow_null=True)
    last4 = serializers.CharField(allow_blank=True, allow_null=True)
    expMonth = serializers.IntegerField(allow_null=True)
    expYear = serializers.IntegerField(allow_null=True)


class BillingInvoiceSerializer(serializers.Serializer):
    periodMonth = serializers.CharField()
    amountEur = serializers.FloatField()
    currency = serializers.CharField()
    status = serializers.CharField()
    paidAt = serializers.DateTimeField(allow_null=True)
    hostedInvoiceUrl = serializers.URLField(allow_blank=True, allow_null=True)
    invoicePdf = serializers.URLField(allow_blank=True, allow_null=True)
    lastError = serializers.CharField(allow_blank=True, allow_null=True)


class BillingStatusSerializer(serializers.Serializer):
    paymentMethodReady = serializers.BooleanField()
    stripeCustomerReady = serializers.BooleanField()
    card = BillingCardSerializer(allow_null=True)
    latestInvoice = BillingInvoiceSerializer(allow_null=True)


class BillingSetupSessionSerializer(serializers.Serializer):
    checkoutUrl = serializers.URLField()
    sessionId = serializers.CharField()


class ProviderMonthlyCostSerializer(serializers.Serializer):
    provider = serializers.CharField()
    providerAmount = serializers.FloatField()
    amountWithMarkup = serializers.FloatField()
    totalWithVat = serializers.FloatField()
    currency = serializers.CharField()
    source = serializers.CharField()
    fetchedAt = serializers.DateTimeField(allow_null=True)
    metadata = serializers.JSONField()


class BillingMonthlySummarySerializer(serializers.Serializer):
    periodMonth = serializers.CharField()
    amountEur = serializers.FloatField()
    subtotalWithMarkupEur = serializers.FloatField()
    totalWithVatEur = serializers.FloatField()
    veraTotalWithVatEur = serializers.FloatField()
    currency = serializers.CharField()
    chargeDate = serializers.DateField()
    isFresh = serializers.BooleanField()
    refreshError = serializers.CharField(allow_blank=True, allow_null=True)
    invoice = BillingInvoiceSerializer(allow_null=True)
    providerCosts = ProviderMonthlyCostSerializer(many=True)
    costBreakdown = serializers.JSONField()
