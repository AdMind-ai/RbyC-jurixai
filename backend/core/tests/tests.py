from django.contrib.auth import get_user_model
from django.test import override_settings
from django.test import TestCase
from django.utils import timezone
from datetime import datetime
from unittest.mock import Mock, patch

from rest_framework.test import APIClient

from core.models.usage import UsageRecord, UsageTool
from core.services.document_retrieval.intent_classifier import (
	INTENT_CROSS_DOCUMENT_COVERAGE,
	INTENT_ORGANIZATIONAL_STRUCTURE_YEAR_COMPARISON,
	classify_document_search_intent,
)
from core.services.document_retrieval.prompt_context import build_document_search_input
from core.services.document_retrieval.retrieval_strategies import get_retrieval_strategy
from core.services.usage_service import UsageReportFilters, UsageReportService
from core.services.usage_tracking import UsageTrackingService
from integrations.models import (
	IntegrationApiKey,
	IntegrationClient,
	IntegrationUsageRecord,
)


class UsageTrackingServiceTests(TestCase):
	def setUp(self):
		user_model = get_user_model()
		self.user = user_model.objects.create_user(
			email="usage-test@example.com",
			username="usage-test",
			password="secret123",
		)

	def test_record_usage_event_always_saves_one_interaction(self):
		result = UsageTrackingService.record_usage_event(
			user=self.user,
			tool=UsageTool.CHAT_ASSISTANT,
			quantity=7,
			metadata={"source": "test"},
		)

		self.assertIsNotNone(result)
		self.assertEqual(str(result.record.quantity), "1")
		self.assertEqual(result.record.metadata, {"source": "test"})


class CheckComplianceAnalyzeViewTests(TestCase):
	def setUp(self):
		user_model = get_user_model()
		self.user = user_model.objects.create_user(
			email="compliance-test@example.com",
			username="compliance-test",
			password="secret123",
		)
		self.client = APIClient()
		self.client.force_authenticate(user=self.user)
		self.payload = {
			"files": [
				{
					"name": "contract.pdf",
					"mimeType": "application/pdf",
					"data": "JVBERi0xLjQ=",
				}
			],
			"norms": ["GDPR (General Data Protection Regulation)"],
		}

	@override_settings(OPENAI_PROMPT_ID_CHECK_COMPLIANCE_RBYC="pmpt_test")
	@patch("core.views.check_compliance_view.client.responses.create")
	def test_analyze_without_custom_database_does_not_send_mcp_tool(self, mock_create):
		mock_create.return_value = Mock(
			output_text='{"segments":[{"text":"Clause text","issue":null}]}'
		)

		response = self.client.post(
			"/api/openai/check-compliance/analyze/",
			self.payload,
			format="json",
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data["segments"][0]["text"], "Clause text")
		request_kwargs = mock_create.call_args.kwargs
		self.assertNotIn("tools", request_kwargs)

	@override_settings(
		OPENAI_PROMPT_ID_CHECK_COMPLIANCE_RBYC="pmpt_test",
		CHECK_COMPLIANCE_MCP_SERVER_URL="https://mcp.example.test/sse",
	)
	@patch("core.views.check_compliance_view.client.responses.create")
	def test_analyze_with_custom_database_sends_mcp_tool(self, mock_create):
		mock_create.return_value = Mock(
			output_text='{"segments":[{"text":"Clause text","issue":null}]}'
		)
		payload = {
			**self.payload,
			"norms": [
				"GDPR (General Data Protection Regulation)",
				"Database customizzato",
			],
		}

		response = self.client.post(
			"/api/openai/check-compliance/analyze/",
			payload,
			format="json",
		)

		self.assertEqual(response.status_code, 200)
		request_kwargs = mock_create.call_args.kwargs
		self.assertEqual(request_kwargs["tools"][0]["type"], "mcp")
		self.assertEqual(
			request_kwargs["tools"][0]["server_url"],
			"https://mcp.example.test/sse",
		)


class UsageReportServiceMonthTests(TestCase):
	def setUp(self):
		user_model = get_user_model()
		self.user = user_model.objects.create_user(
			email="usage-months@example.com",
			username="usage-months",
			password="secret123",
		)

	def test_list_available_months_returns_unique_months(self):
		tz = timezone.get_current_timezone()
		records = [
			UsageRecord(
				user=self.user,
				tool=UsageTool.CHECK_COMPLIANCE,
				occurred_at=timezone.make_aware(datetime(2026, 4, 1, 10, 0), tz),
			),
			UsageRecord(
				user=self.user,
				tool=UsageTool.CHAT_ASSISTANT,
				occurred_at=timezone.make_aware(datetime(2026, 4, 20, 10, 0), tz),
			),
			UsageRecord(
				user=self.user,
				tool=UsageTool.DRAFT_DOCUMENT,
				occurred_at=timezone.make_aware(datetime(2026, 3, 15, 10, 0), tz),
			),
		]
		UsageRecord.objects.bulk_create(records)

		months = list(UsageReportService.list_available_months(UsageReportFilters()))

		self.assertEqual(
			months,
			[
				{"value": "2026-04", "label": "Aprile 2026"},
				{"value": "2026-03", "label": "Marzo 2026"},
			],
		)

	def test_build_report_includes_integration_usage_breakdown(self):
		tz = timezone.get_current_timezone()
		UsageRecord.objects.create(
			user=self.user,
			tool=UsageTool.RICERCA_DOCUMENTALE,
			occurred_at=timezone.make_aware(datetime(2026, 4, 4, 10, 0), tz),
		)
		integration_client = IntegrationClient.objects.create(
			client_name="Customer 0047",
			customer_code="customer0047",
			bucket_name="customer0047",
			active=True,
		)
		api_key = IntegrationApiKey.objects.create(
			client=integration_client,
			key_hash=IntegrationApiKey.hash_key("usage-integration-key"),
			active=True,
			description="produzione",
		)
		IntegrationUsageRecord.objects.create(
			client=integration_client,
			api_key=api_key,
			tool="RICERCA_DOCUMENTALE",
			auth_mode="api_key",
			auth_identifier="produzione",
			occurred_at=timezone.make_aware(datetime(2026, 4, 12, 12, 0), tz),
		)

		report = UsageReportService.build_report(UsageReportFilters(month="2026-04"))

		self.assertEqual(report["totalRequests"], 2)
		self.assertEqual(report["toolUsage"][UsageTool.RICERCA_DOCUMENTALE]["count"], 2)
		self.assertEqual(len(report["userBreakdown"]), 1)
		self.assertEqual(len(report["integrationBreakdown"]), 1)
		self.assertEqual(report["integrationBreakdown"][0]["clientName"], "Customer 0047")
		self.assertEqual(report["integrationBreakdown"][0]["apiKeys"][0]["label"], "produzione")

	def test_list_available_months_includes_integration_only_months(self):
		tz = timezone.get_current_timezone()
		integration_client = IntegrationClient.objects.create(
			client_name="Customer 0047",
			customer_code="customer0047",
			bucket_name="customer0047",
			active=True,
		)
		IntegrationUsageRecord.objects.create(
			client=integration_client,
			tool="RICERCA_DOCUMENTALE",
			auth_mode="legacy_shared_key",
			auth_identifier="legacy_shared_key",
			occurred_at=timezone.make_aware(datetime(2026, 5, 2, 9, 0), tz),
		)

		months = list(UsageReportService.list_available_months(UsageReportFilters()))

		self.assertEqual(months[0], {"value": "2026-05", "label": "Maggio 2026"})


class DocumentSearchIntentClassifierTests(TestCase):
	def test_classify_rso_query_as_organizational_structure_intent(self):
		classification = classify_document_search_intent(
			"Quando e stata approvata l'ultima RSO?"
		)

		self.assertEqual(
			classification.intent_type,
			INTENT_ORGANIZATIONAL_STRUCTURE_YEAR_COMPARISON,
		)
		self.assertIn("rso", classification.matched_signals)

	def test_classify_board_topic_count_query_as_cross_document_coverage(self):
		classification = classify_document_search_intent(
			"Quante volte in cda si e parlato di un tema operativo?"
		)

		self.assertEqual(classification.intent_type, INTENT_CROSS_DOCUMENT_COVERAGE)
		self.assertIn("quante volte", classification.matched_signals)
		self.assertIn("cda", classification.matched_signals)

	def test_cross_document_coverage_context_preserves_transversal_guidance(self):
		classification = classify_document_search_intent(
			"Quando si e parlato in cda di una banca depositaria?"
		)
		strategy = get_retrieval_strategy(classification.intent_type)

		model_input = build_document_search_input(
			"Quando si e parlato in cda di una banca depositaria?",
			classification,
			strategy,
		)

		self.assertIn("intent_type=cross_document_coverage", model_input)
		self.assertIn("preferred_document_families=verbale_cda,estratto_cda", model_input)
		self.assertIn("evidence_plan=", model_input)
		self.assertIn("candidate set", model_input)
		self.assertIn("candidati meno alti in ranking", model_input)
		self.assertIn("non ometterli senza un criterio esplicito", model_input)
