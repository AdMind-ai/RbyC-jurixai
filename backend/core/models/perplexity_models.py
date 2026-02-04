import uuid
from django.db import models


class PerplexityConversation(models.Model):
    """Persistent thread for Perplexity chats."""
    conversation_id = models.CharField(
        max_length=40,
        unique=True,
        default=uuid.uuid4,
        editable=False,
    )
    title = models.CharField(max_length=255, blank=True)
    memory_summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title or self.conversation_id


class PerplexityMessage(models.Model):
    ROLE_CHOICES = (
        ("system", "system"),
        ("user", "user"),
        ("assistant", "assistant"),
    )

    conversation = models.ForeignKey(
        PerplexityConversation,
        related_name="messages",
        on_delete=models.CASCADE,
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    included_in_summary = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}: {self.conversation.conversation_id}"
