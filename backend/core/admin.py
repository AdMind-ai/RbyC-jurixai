from django.contrib import admin
from core.models.openai_chat_models import ChatConversation, ChatMessage
from core.models.assistant_thread_model import AssistantThread
# Register your models here.


class ChatMessageInline(admin.StackedInline):
    model = ChatMessage
    extra = 0


class AssistantThreadInline(admin.StackedInline):
    model = AssistantThread
    extra = 0
    readonly_fields = ('thread_id', 'created_at', 'active')


@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'created_at')
    list_filter = ('created_at', 'name')
    inlines = [ChatMessageInline, AssistantThreadInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'content', 'is_user', 'created_at')
    list_filter = ('created_at', 'is_user')
    search_fields = ('content',)


@admin.register(AssistantThread)
class AssistantThreadAdmin(admin.ModelAdmin):
    list_display = ("thread_id", "conversation", "created_at", "active")
    list_filter = ("active", "created_at")
    search_fields = ("thread_id",)