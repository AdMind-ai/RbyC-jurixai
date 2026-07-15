import uuid

from django.conf import settings
from django.db import models


class CheckComplianceConversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="check_compliance_conversations",
    )
    title = models.CharField(max_length=255, default="Analisi compliance")
    vera_session_id = models.CharField(max_length=128, db_index=True)
    is_saved = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "is_saved"]),
            models.Index(fields=["user", "vera_session_id"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.vera_session_id})"


class CheckComplianceMessage(models.Model):
    ROLE_CHOICES = (
        ("user", "user"),
        ("assistant", "assistant"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        CheckComplianceConversation,
        related_name="messages",
        on_delete=models.CASCADE,
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField(blank=True)
    provider_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role} @ {self.conversation_id}"


class CheckComplianceAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        CheckComplianceConversation,
        related_name="attachments",
        on_delete=models.CASCADE,
    )
    message = models.ForeignKey(
        CheckComplianceMessage,
        related_name="attachments",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    bucket = models.CharField(max_length=255)
    s3_key = models.TextField()
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=255, blank=True)
    size = models.BigIntegerField(default=0)
    version_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation"]),
        ]

    def __str__(self):
        return self.filename
