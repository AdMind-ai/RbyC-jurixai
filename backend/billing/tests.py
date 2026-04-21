from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from billing.models import ProviderCostProvider, ProviderCostSource, ProviderMonthlyCost, ProviderUsageCost
from billing.services.provider_costs import ProviderCostService
from billing.services.provider_usage_costs import ProviderUsageCostService


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

    def test_refresh_keeps_manual_gemini_cost(self):
        ProviderCostService.upsert_provider_cost(
            provider=ProviderCostProvider.GEMINI,
            period_month=self.period_month,
            amount=Decimal("12.5000"),
            currency="EUR",
            source=ProviderCostSource.MANUAL,
            metadata={"note": "admin launch"},
        )

        with override_settings(OPENAI_ADMIN_KEY=None):
            costs = ProviderCostService.refresh_monthly_costs(self.period_month)

        gemini_cost = next(cost for cost in costs if cost.provider == ProviderCostProvider.GEMINI)
        self.assertEqual(gemini_cost.source, ProviderCostSource.MANUAL)
        self.assertEqual(gemini_cost.provider_amount, Decimal("12.5000"))
        self.assertEqual(gemini_cost.metadata, {"note": "admin launch"})

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

    def test_total_uses_preserved_manual_and_estimated_costs(self):
        ProviderCostService.upsert_provider_cost(
            provider=ProviderCostProvider.GEMINI,
            period_month=self.period_month,
            amount=Decimal("10.0000"),
            currency="EUR",
            source=ProviderCostSource.MANUAL,
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

    def test_refresh_perplexity_cost_aggregates_provider_usage_cost_entries(self):
        ProviderUsageCostService.record_perplexity_usage_cost(
            usage_payload={"cost": {"total_cost": 1.2500, "currency": "USD"}},
            external_request_id="pplx-req-1",
        )
        ProviderUsageCostService.record_perplexity_usage_cost(
            usage_payload={"cost": {"total_cost": 2.5000, "currency": "USD"}},
            external_request_id="pplx-req-2",
        )

        cost = ProviderCostService.refresh_perplexity_cost(self.period_month)

        self.assertEqual(cost.source, ProviderCostSource.ACTUAL_API)
        self.assertEqual(cost.provider, ProviderCostProvider.PERPLEXITY)
        self.assertEqual(cost.provider_amount, Decimal("3.7500"))
        self.assertEqual(cost.currency, "EUR")
        self.assertEqual(cost.metadata["entry_count"], 2)
        self.assertEqual(cost.metadata["provider_currency"], "USD")
