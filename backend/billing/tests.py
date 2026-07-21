from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import boto3
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from billing.models import (
    BillingAccount,
    ProviderCostProvider,
    ProviderCostSource,
    ProviderUsageCost,
    Wallet,
    WalletTransaction,
    WalletTransactionType,
)
from billing.services.ai_usage_costs import AIUsageCostService
from billing.services.provider_costs import ProviderCostService
from billing.services.provider_usage_costs import ProviderUsageCostService
from billing.services.aws_costs import AwsCostExplorerService
from billing.services.internal_costs import build_internal_costs_payload
from billing.services.wallet import WalletService
from core.models.notification_model import Notification, NotificationType
from core.models.vera_usage_model import VeraUsageRecord
from core.tasks import notify_wallet_credit_usage_thresholds


class ProviderUsageCostServiceTests(SimpleTestCase):
    def test_extract_perplexity_usage_metadata_returns_cost_payload(self):
        chunk = SimpleNamespace(
            id="req_123",
            usage=SimpleNamespace(
                prompt_tokens=120,
                completion_tokens=45,
                total_tokens=165,
                citation_tokens=10,
                num_search_queries=2,
                reasoning_tokens=5,
                search_context_size="medium",
                cost=SimpleNamespace(
                    input_tokens_cost=0.12,
                    output_tokens_cost=0.34,
                    total_cost=0.56,
                    citation_tokens_cost=0.01,
                    reasoning_tokens_cost=0.02,
                    request_cost=0.03,
                    search_queries_cost=0.04,
                ),
            ),
        )

        request_id = ProviderUsageCostService.extract_perplexity_request_id(chunk)
        metadata = ProviderUsageCostService.extract_perplexity_usage_metadata(chunk)

        self.assertEqual(request_id, "req_123")
        self.assertEqual(metadata["prompt_tokens"], 120)
        self.assertEqual(metadata["completion_tokens"], 45)
        self.assertEqual(metadata["cost"]["total_cost"], 0.56)
        self.assertEqual(metadata["cost"]["currency"], "USD")


class WalletServiceTests(TestCase):
    def test_wallet_solo_uses_configured_defaults(self):
        with override_settings(
            WALLET_DEFAULT_RECHARGE_AMOUNT_EUR="100.00",
            WALLET_DEFAULT_THRESHOLD_EUR="5.00",
        ):
            wallet = Wallet.get_solo()

        self.assertEqual(wallet.balance_eur, Decimal("0.00"))
        self.assertEqual(wallet.recharge_amount_eur, Decimal("100.00"))
        self.assertEqual(wallet.threshold_eur, Decimal("5.00"))
        self.assertTrue(wallet.auto_recharge_enabled)

    def test_credit_and_debit_are_idempotent(self):
        credit = WalletService.credit(
            amount_eur=Decimal("100.00"),
            description="Admin gift",
            idempotency_key="gift-1",
        )
        repeated_credit = WalletService.credit(
            amount_eur=Decimal("100.00"),
            description="Admin gift",
            idempotency_key="gift-1",
        )
        debit = WalletService.debit_usage(
            amount_eur=Decimal("12.50"),
            description="AI usage",
            idempotency_key="usage-1",
        )
        repeated_debit = WalletService.debit_usage(
            amount_eur=Decimal("12.50"),
            description="AI usage",
            idempotency_key="usage-1",
        )

        wallet = Wallet.get_solo()
        self.assertEqual(credit.id, repeated_credit.id)
        self.assertEqual(debit.id, repeated_debit.id)
        self.assertEqual(wallet.balance_eur, Decimal("87.50"))
        self.assertEqual(WalletTransaction.objects.count(), 2)
        self.assertEqual(debit.transaction_type, WalletTransactionType.USAGE_DEBIT)
        self.assertEqual(debit.amount_eur, Decimal("-12.50"))

    def test_wallet_credit_usage_threshold_notifications_are_per_credit_cycle(self):
        credit = WalletService.credit(
            amount_eur=Decimal("100.00"),
            description="Credito iniziale",
            idempotency_key="wallet-credit-threshold-test",
        )
        WalletService.debit_usage(
            amount_eur=Decimal("20.00"),
            description="Consumo AI",
            idempotency_key="wallet-debit-20",
        )

        result = notify_wallet_credit_usage_thresholds()
        self.assertEqual(result["status"], "created")
        self.assertEqual(result["threshold"], 20)
        self.assertTrue(
            Notification.objects.filter(
                notification_type=NotificationType.CONSUMPTION_THRESHOLD,
                reference_type="wallet_credit_usage",
                reference_id=f"{credit.id}:20",
            ).exists()
        )

        repeated = notify_wallet_credit_usage_thresholds()
        self.assertEqual(repeated["status"], "already_notified")

        WalletService.debit_usage(
            amount_eur=Decimal("20.00"),
            description="Consumo AI",
            idempotency_key="wallet-debit-40",
        )

        next_result = notify_wallet_credit_usage_thresholds()
        self.assertEqual(next_result["status"], "created")
        self.assertEqual(next_result["threshold"], 40)

    def test_ai_usage_debit_only_records_monthly_delta(self):
        period_month = date(2026, 7, 1)
        wallet = Wallet.get_solo()
        wallet.auto_recharge_enabled = False
        wallet.save(update_fields=["auto_recharge_enabled", "updated_at"])

        first_summary = SimpleNamespace(
            total_with_vat=Decimal("5.17"),
            rbyc_raw=Decimal("0.00"),
            vera_raw=Decimal("4.2377"),
        )
        second_summary = SimpleNamespace(
            total_with_vat=Decimal("7.00"),
            rbyc_raw=Decimal("0.00"),
            vera_raw=Decimal("5.7377"),
        )

        with patch.object(AIUsageCostService, "build_monthly_summary", return_value=first_summary):
            first_result = WalletService.debit_ai_usage_for_month(period_month)
        with patch.object(AIUsageCostService, "build_monthly_summary", return_value=first_summary):
            repeated_result = WalletService.debit_ai_usage_for_month(period_month)
        with patch.object(AIUsageCostService, "build_monthly_summary", return_value=second_summary):
            second_result = WalletService.debit_ai_usage_for_month(period_month)

        wallet.refresh_from_db()
        self.assertEqual(first_result["status"], "debited")
        self.assertEqual(repeated_result["status"], "no_delta")
        self.assertEqual(second_result["delta_eur"], "1.83")
        self.assertEqual(wallet.balance_eur, Decimal("-7.00"))
        self.assertEqual(WalletTransaction.objects.count(), 2)
        self.assertEqual(
            WalletTransaction.objects.aggregate(total=Sum("amount_eur"))["total"],
            Decimal("-7.00"),
        )


class WalletViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="wallet-admin@example.com",
            username="wallet-admin",
            password="secret123",
            is_staff=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_wallet_status_returns_wallet_and_payment_method(self):
        account = BillingAccount.get_solo()
        account.payment_method_ready = True
        account.card_brand = "visa"
        account.card_last4 = "4242"
        account.card_exp_month = 12
        account.card_exp_year = 2030
        account.save()
        WalletService.credit(amount_eur=Decimal("20.00"), description="Initial credit")

        response = self.client.get("/api/billing/wallet/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["balanceEur"], 20.0)
        self.assertTrue(response.data["paymentMethodReady"])
        self.assertEqual(response.data["card"]["last4"], "4242")

    def test_wallet_transactions_returns_history(self):
        WalletService.credit(amount_eur=Decimal("30.00"), description="Initial credit")

        response = self.client.get("/api/billing/wallet/transactions/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["amountEur"], 30.0)


class ProviderCostServiceTests(TestCase):
    def setUp(self):
        self.period_month = date(2026, 4, 1)

    def test_refresh_monthly_costs_returns_openai_only(self):
        with override_settings(OPENAI_ADMIN_KEY=None):
            costs = ProviderCostService.refresh_monthly_costs(self.period_month)

        self.assertEqual(
            [cost.provider for cost in costs],
            [ProviderCostProvider.OPENAI],
        )

    @override_settings(
        AI_USAGE_BILLING_START_DATE=None,
        RBYC_OPENAI_PROJECT_ID=None,
        OPENAI_COSTS_PROJECT_ID=None,
        OPENAI_PROJECT_ID=None,
    )
    def test_actual_api_overrides_not_configured(self):
        ProviderCostService.ensure_not_configured_cost(
            provider=ProviderCostProvider.OPENAI,
            period_month=self.period_month,
            reason="Missing key.",
        )

        payload = {
            "data": [
                {
                    "results": [
                        {
                            "project_id": None,
                            "amount": {"value": 10, "currency": "USD"},
                        }
                    ]
                }
            ]
        }

        with override_settings(OPENAI_ADMIN_KEY="test-key"):
            with patch.object(
                ProviderCostService,
                "_fetch_openai_cost_payload",
                return_value=payload,
            ):
                openai_cost = ProviderCostService.refresh_openai_cost(self.period_month)

        self.assertEqual(openai_cost.source, ProviderCostSource.ACTUAL_API)
        self.assertEqual(openai_cost.provider_amount, Decimal("10.0000"))
        self.assertEqual(openai_cost.currency, "EUR")
        self.assertEqual(openai_cost.metadata.get("provider_currency"), "USD")

    @override_settings(
        OPENAI_ADMIN_KEY="test-key",
        AI_USAGE_BILLING_START_DATE="2026-04-15",
        RBYC_OPENAI_PROJECT_ID=None,
        OPENAI_COSTS_PROJECT_ID=None,
        OPENAI_PROJECT_ID=None,
    )
    def test_refresh_openai_cost_only_counts_billable_buckets(self):
        payload = {
            "data": [
                {
                    "start_time": int(datetime(2026, 4, 10, tzinfo=timezone.utc).timestamp()),
                    "results": [
                        {
                            "project_id": None,
                            "amount": {"value": 100, "currency": "USD"},
                        }
                    ],
                },
                {
                    "start_time": int(datetime(2026, 4, 15, tzinfo=timezone.utc).timestamp()),
                    "results": [
                        {
                            "project_id": None,
                            "amount": {"value": 25, "currency": "USD"},
                        }
                    ],
                },
            ]
        }

        with patch.object(
            ProviderCostService,
            "_fetch_openai_cost_payload",
            return_value=payload,
        ):
            openai_cost = ProviderCostService.refresh_openai_cost(self.period_month)

        self.assertEqual(openai_cost.provider_amount, Decimal("25.0000"))
        self.assertEqual(openai_cost.metadata.get("raw_provider_amount"), "125.0000")
        self.assertEqual(openai_cost.metadata.get("billing_start_date"), "2026-04-15")

    def test_total_uses_billable_providers_only(self):
        ProviderCostService.upsert_provider_cost(
            provider=ProviderCostProvider.OPENAI,
            period_month=self.period_month,
            amount=Decimal("10.0000"),
            currency="EUR",
            source=ProviderCostSource.ESTIMATED,
        )
        ProviderCostService.upsert_provider_cost(
            provider=ProviderCostProvider.PERPLEXITY,
            period_month=self.period_month,
            amount=Decimal("5.0000"),
            currency="EUR",
            source=ProviderCostSource.ESTIMATED,
        )

        total = ProviderCostService.get_total_for_month(self.period_month, refresh=False)

        self.assertEqual(total.currency, "EUR")
        self.assertEqual(len(total.costs), 1)
        self.assertEqual(
            [cost.provider for cost in total.costs],
            [ProviderCostProvider.OPENAI],
        )
        self.assertEqual(total.amount, Decimal("14.64"))

    def test_recorded_perplexity_request_cost_is_stored_separately_from_usage(self):
        usage_payload = {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
            "cost": {
                "total_cost": 0.5600,
                "currency": "USD",
            },
        }

        cost = ProviderUsageCostService.record_perplexity_usage_cost(
            usage_payload=usage_payload,
            external_request_id="pplx-req-1",
            metadata={"conversation_id": "abc"},
        )

        self.assertEqual(ProviderUsageCost.objects.count(), 1)
        self.assertEqual(cost.provider, ProviderCostProvider.PERPLEXITY)
        self.assertEqual(cost.external_request_id, "pplx-req-1")
        self.assertEqual(cost.amount, Decimal("0.5600"))
        self.assertEqual(cost.currency, "EUR")
        self.assertEqual(cost.provider_currency, "USD")
        self.assertEqual(cost.raw_payload, usage_payload)
        self.assertEqual(cost.metadata, {"conversation_id": "abc"})


class AIUsageCostServiceTests(TestCase):
    def setUp(self):
        self.period_month = date(2026, 4, 1)

    @override_settings(
        AI_USAGE_RBYC_MARKUP_PERCENTAGE="20",
        AI_USAGE_VERA_MARKUP_PERCENTAGE="25",
        AI_USAGE_IVA_PERCENTAGE="22",
        AI_USAGE_BILLING_START_DATE=None,
    )
    def test_build_monthly_summary_applies_distinct_markups(self):
        ProviderCostService.upsert_provider_cost(
            provider=ProviderCostProvider.OPENAI,
            period_month=self.period_month,
            amount=Decimal("100.0000"),
            currency="EUR",
            source=ProviderCostSource.ACTUAL_API,
        )
        VeraUsageRecord.objects.create(
            date=date(2026, 4, 10),
            provider="openai",
            model="vera-openai",
            cost_eur=Decimal("20.000000"),
        )
        VeraUsageRecord.objects.create(
            date=date(2026, 4, 11),
            provider="anthropic",
            model="vera-claude",
            cost_eur=Decimal("30.000000"),
        )

        summary = AIUsageCostService.build_monthly_summary(
            self.period_month,
            refresh_rbyc=False,
            refresh_vera=False,
        )

        self.assertEqual(summary.rbyc_with_markup, Decimal("120.0000"))
        self.assertEqual(summary.vera_with_markup, Decimal("62.5000"))
        self.assertEqual(summary.total_with_markup, Decimal("182.50"))
        self.assertEqual(summary.total_with_vat, Decimal("222.65"))
        self.assertEqual(summary.vera_total_with_vat, Decimal("76.25"))

        payload = AIUsageCostService.serialize_for_billing(
            self.period_month,
            refresh_rbyc=False,
            refresh_vera=False,
        )

        self.assertEqual(payload["amountEur"], 182.5)
        self.assertEqual(payload["totalWithVatEur"], 222.65)

    @override_settings(
        AI_USAGE_RBYC_MARKUP_PERCENTAGE="20",
        AI_USAGE_VERA_MARKUP_PERCENTAGE="25",
        AI_USAGE_IVA_PERCENTAGE="22",
        AI_USAGE_BILLING_START_DATE="2026-04-15",
    )
    def test_build_monthly_summary_excludes_vera_costs_before_billing_start(self):
        ProviderCostService.upsert_provider_cost(
            provider=ProviderCostProvider.OPENAI,
            period_month=self.period_month,
            amount=Decimal("0.0000"),
            currency="EUR",
            source=ProviderCostSource.ACTUAL_API,
        )
        VeraUsageRecord.objects.create(
            date=date(2026, 4, 10),
            provider="openai",
            model="vera-openai-before",
            cost_eur=Decimal("100.000000"),
        )
        VeraUsageRecord.objects.create(
            date=date(2026, 4, 15),
            provider="openai",
            model="vera-openai-after",
            cost_eur=Decimal("20.000000"),
        )
        VeraUsageRecord.objects.create(
            date=date(2026, 4, 16),
            provider="anthropic",
            model="vera-claude-after",
            cost_eur=Decimal("30.000000"),
        )

        summary = AIUsageCostService.build_monthly_summary(
            self.period_month,
            refresh_rbyc=False,
            refresh_vera=False,
        )

        self.assertEqual(summary.vera_openai_raw, Decimal("20.0000"))
        self.assertEqual(summary.vera_anthropic_raw, Decimal("30.0000"))
        self.assertEqual(summary.vera_total_with_vat, Decimal("76.25"))


@override_settings(
    INTERNAL_COSTS_TOKEN="internal-test-token",
    INTERNAL_COSTS_PROJECT_ID="rbyc",
    INTERNAL_COSTS_PROJECT_NAME="Rbyc",
    INTERNAL_COSTS_DEFAULT_CURRENCY="EUR",
    INTERNAL_COSTS_AWS_REGION="us-east-1",
)
class InternalCostsEndpointTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    def test_requires_bearer_token(self):
        response = self.client.get("/api/internal/costs")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Unauthorized.")

    @patch("billing.views.build_internal_costs_payload")
    def test_returns_payload_when_token_is_valid(self, build_payload_mock):
        build_payload_mock.return_value = {
            "version": "v1",
            "projectId": "rbyc",
            "projectName": "Rbyc",
            "currency": "EUR",
            "generatedAt": "2026-05-26T14:30:00Z",
            "period": {
                "start": "2026-05-01T00:00:00Z",
                "end": "2026-06-01T00:00:00Z",
                "month": "2026-05",
            },
            "totals": {"ai": 10.0, "infra": 20.0, "total": 30.0},
            "monthlyBreakdown": [],
            "items": [],
            "status": {"overall": "ok", "ai": "ok", "infra": "ok"},
            "errors": [],
        }

        response = self.client.get(
            "/api/internal/costs?month=2026-05",
            HTTP_AUTHORIZATION="Bearer internal-test-token",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["projectId"], "rbyc")
        build_payload_mock.assert_called_once_with("2026-05")


@override_settings(
    INTERNAL_COSTS_PROJECT_ID="rbyc",
    INTERNAL_COSTS_PROJECT_NAME="Rbyc",
    INTERNAL_COSTS_TOKEN="internal-test-token",
    INTERNAL_COSTS_DEFAULT_CURRENCY="EUR",
)
class InternalCostsPayloadTests(TestCase):
    @patch("billing.services.internal_costs.collect_ai_costs")
    @patch("billing.services.internal_costs._collect_aws_costs")
    @patch("billing.services.internal_costs.EuropeanCentralBankFxService.get_quote")
    def test_returns_partial_when_infra_fails(self, fx_quote_mock, collect_aws_mock, collect_ai_mock):
        from billing.services.internal_costs import CostCollectionResult
        from billing.services.fx_rates import FxQuote

        fx_quote_mock.return_value = FxQuote(
            base_currency="USD",
            quote_currency="EUR",
            rate=Decimal("0.90"),
            fx_date="2026-05-31",
            source="ecb",
        )

        collect_ai_mock.return_value = CostCollectionResult(
            items=[
                {
                    "category": "ai",
                    "provider": "openai",
                    "service": "gpt-4.1-mini",
                    "label": "OpenAI API",
                    "amount": 12.5,
                    "currency": "USD",
                    "periodMonth": "2026-05",
                    "metadata": {"source": "provider_usage_costs"},
                }
            ],
            total=Decimal("12.50"),
            status="ok",
            errors=[],
        )
        collect_aws_mock.side_effect = RuntimeError("AWS unavailable")

        payload = build_internal_costs_payload("2026-05")

        self.assertEqual(payload["status"]["overall"], "partial")
        self.assertEqual(payload["status"]["ai"], "ok")
        self.assertEqual(payload["status"]["infra"], "error")
        self.assertEqual(payload["currency"], "EUR")
        self.assertEqual(payload["totals"]["ai"], 11.25)
        self.assertEqual(payload["totals"]["infra"], 0.0)
        self.assertEqual(payload["items"][0]["currency"], "EUR")
        self.assertEqual(payload["items"][0]["metadata"]["originalCurrency"], "USD")
        self.assertEqual(payload["items"][0]["metadata"]["fxRate"], 0.9)
        self.assertEqual(payload["items"][0]["metadata"]["fxSource"], "ecb")
        self.assertEqual(payload["errors"][0]["scope"], "infra")

    @patch("billing.services.internal_costs.collect_ai_costs")
    @patch("billing.services.internal_costs._collect_aws_costs")
    @patch("billing.services.internal_costs.EuropeanCentralBankFxService.get_quote")
    def test_converts_aws_items_and_recalculates_totals_in_eur(self, fx_quote_mock, collect_aws_mock, collect_ai_mock):
        from billing.services.internal_costs import CostCollectionResult
        from billing.services.fx_rates import FxQuote

        fx_quote_mock.return_value = FxQuote(
            base_currency="USD",
            quote_currency="EUR",
            rate=Decimal("0.90"),
            fx_date="2026-05-31",
            source="ecb",
        )

        collect_ai_mock.return_value = CostCollectionResult(
            items=[
                {
                    "category": "ai",
                    "provider": "openai",
                    "service": "openai",
                    "label": "OpenAI API",
                    "amount": 3.24,
                    "currency": "EUR",
                    "periodMonth": "2026-05",
                    "metadata": {"source": "actual_api"},
                }
            ],
            total=Decimal("3.24"),
            status="ok",
            errors=[],
        )
        collect_aws_mock.return_value = CostCollectionResult(
            items=[
                {
                    "category": "infra",
                    "provider": "aws",
                    "service": "lightsail",
                    "label": "AWS Lightsail",
                    "amount": 24.48,
                    "currency": "USD",
                    "periodMonth": "2026-05",
                    "metadata": {"aws_service_name": "Amazon Lightsail"},
                },
                {
                    "category": "infra",
                    "provider": "aws",
                    "service": "s3",
                    "label": "AWS S3",
                    "amount": 1.90,
                    "currency": "USD",
                    "periodMonth": "2026-05",
                    "metadata": {"aws_service_name": "Amazon Simple Storage Service"},
                },
            ],
            total=Decimal("26.38"),
            status="ok",
            errors=[],
        )

        payload = build_internal_costs_payload("2026-05")

        self.assertEqual(payload["currency"], "EUR")
        self.assertEqual(payload["monthlyBreakdown"][0]["currency"], "EUR")
        self.assertEqual(payload["totals"]["ai"], 3.24)
        self.assertEqual(payload["totals"]["infra"], 23.74)
        self.assertEqual(payload["totals"]["total"], 26.98)
        infra_items = [item for item in payload["items"] if item["category"] == "infra"]
        self.assertEqual([item["currency"] for item in infra_items], ["EUR", "EUR"])
        self.assertEqual(infra_items[0]["metadata"]["aws_service_name"], "Amazon Lightsail")
        self.assertEqual(infra_items[0]["metadata"]["originalAmount"], 24.48)
        self.assertEqual(infra_items[0]["metadata"]["originalCurrency"], "USD")
        self.assertEqual(infra_items[0]["metadata"]["fxRate"], 0.9)
        self.assertEqual(infra_items[0]["metadata"]["fxDate"], "2026-05-31")
        self.assertEqual(infra_items[0]["metadata"]["fxSource"], "ecb")


@override_settings(
    INTERNAL_COSTS_AWS_REGION="us-east-1",
)
class AwsCostExplorerServiceTests(SimpleTestCase):
    @patch.object(boto3, "client")
    def test_collect_monthly_costs_groups_services_into_items(self, boto_client_mock):
        boto_client_mock.return_value.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "Groups": [
                        {
                            "Keys": ["Amazon Elastic Compute Cloud - Compute"],
                            "Metrics": {
                                "UnblendedCost": {
                                    "Amount": "180.20",
                                    "Unit": "USD",
                                }
                            },
                        },
                        {
                            "Keys": ["Amazon Relational Database Service"],
                            "Metrics": {
                                "UnblendedCost": {
                                    "Amount": "130.70",
                                    "Unit": "USD",
                                }
                            },
                        },
                    ]
                }
            ]
        }

        result = AwsCostExplorerService.collect_monthly_costs(
            period_month=date(2026, 5, 1),
            currency="USD",
        )

        self.assertEqual(result.total, Decimal("310.90"))
        self.assertEqual(len(result.items), 2)
        self.assertEqual(result.items[0]["service"], "ec2")
        self.assertEqual(result.items[1]["service"], "rds")

