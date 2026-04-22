import uuid
from django.conf import settings
from django.db import models


class StoredChatSession(models.Model):
    class ProviderChoices(models.TextChoices):
        GPT = "gpt", "GPT / OpenAI"
        PERPLEXITY = "perplexity", "Perplexity"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="stored_chat_sessions",
    )
    provider = models.CharField(max_length=20, choices=ProviderChoices.choices)
    external_conversation_id = models.CharField(
        max_length=128,
        blank=True,
        null=True,
    )
    display_model = models.CharField(max_length=64, blank=True)
    title = models.CharField(max_length=255, default="New Chat")
    is_saved = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["provider", "user", "is_saved"]),
            models.Index(fields=["external_conversation_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "provider", "external_conversation_id"],
                name="unique_provider_external_conversation",
            )
        ]

    def __str__(self):
        return f"{self.title} ({self.get_provider_display()})"


class StoredChatMessage(models.Model):
    ROLE_CHOICES = (
        ("system", "system"),
        ("user", "user"),
        ("assistant", "assistant"),
    )

    session = models.ForeignKey(
        StoredChatSession,
        related_name="messages",
        on_delete=models.CASCADE,
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.JSONField(default=list)
    provider_payload = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role} @ {self.session_id}"
