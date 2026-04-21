from django.contrib.auth import get_user_model
from django.test import TestCase

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
