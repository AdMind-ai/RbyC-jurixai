from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import boto3
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from billing.models import ProviderCostProvider, ProviderCostSource, ProviderUsageCost
from billing.services.provider_costs import ProviderCostService
from billing.services.provider_usage_costs import ProviderUsageCostService
from billing.services.aws_costs import AwsCostExplorerService
from billing.services.internal_costs import build_internal_costs_payload


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


class ProviderCostServiceTests(TestCase):
    def setUp(self):
        self.period_month = date(2026, 4, 1)

    def test_refresh_monthly_costs_returns_openai_and_perplexity_only(self):
        with override_settings(OPENAI_ADMIN_KEY=None):
            costs = ProviderCostService.refresh_monthly_costs(self.period_month)

        self.assertEqual(
            [cost.provider for cost in costs],
            [ProviderCostProvider.OPENAI, ProviderCostProvider.PERPLEXITY],
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
        self.assertEqual(len(total.costs), 2)
        self.assertEqual(
            [cost.provider for cost in total.costs],
            [ProviderCostProvider.OPENAI, ProviderCostProvider.PERPLEXITY],
        )
        self.assertEqual(total.amount, Decimal("21.96"))

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

