from django.db import models
from django.conf import settings
from core.models.openai_chat_models import ChatConversation


class AssistantThread(models.Model):
    thread_id = models.CharField(max_length=200, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name="threads",
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "Chat - Thread"
        verbose_name_plural = "Chat - Threads"
