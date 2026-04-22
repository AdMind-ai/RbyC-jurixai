from django.contrib.auth import get_user_model
from django.test import override_settings
from django.test import TestCase
from unittest.mock import Mock, patch

from rest_framework.test import APIClient

from core.models.usage import UsageTool
from core.services.usage_tracking import UsageTrackingService


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
