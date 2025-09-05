from django.db import models
from django.conf import settings
import uuid


class ChatConversation(models.Model):
    id = models.CharField(max_length=40, primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    # Não tem nome único, NÀO ALTERAR!
    name = models.CharField(max_length=100, default="New Chat", unique=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Chat - Conversation"
        verbose_name_plural = "Chat - Conversations"
        # constraints = [
        #     models.UniqueConstraint(
        #         fields=['name'], name='unique_conversation_name')
        # ]

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = str(uuid.uuid4())[:30]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Conversation {self.name} - {self.user.username}"


class ChatMessage(models.Model):
    conversation = models.ForeignKey(
        ChatConversation, related_name='messages', on_delete=models.CASCADE)
    content = models.TextField(blank=True)
    citations = models.JSONField(null=True, blank=True, default=list)
    is_user = models.BooleanField(default=True)

    # If saving files
    file = models.FileField(upload_to="chat/", blank=True, null=True)
    # file_url = models.URLField(max_length=200, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Chat - Message"
        verbose_name_plural = "Chat - Messages"

    def __str__(self):
        return f"Message {self.id} ({'User' if self.is_user else 'AI'})"
