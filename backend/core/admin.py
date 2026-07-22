# Importações dos modelos de openai_chat e assistant_thread
from core.models.openai_chat_models import ChatConversation, ChatMessage
from core.models.assistant_thread_model import AssistantThread
from django.contrib import admin
# ...existing code...
from core.models.segreteria_societaria.company_model import Company
from core.models.segreteria_societaria.officer_model import Officer
from core.models.segreteria_societaria.shareholder_model import Shareholder
from core.models.segreteria_societaria.deadline import Deadline
from core.models.draft_document.company_document_layout import CompanyDocumentLayout
from core.models.usage import UsageRecord
from core.models.vera_usage_model import VeraUsageRecord
from core.models.compliance_log_model import ComplianceLog
from core.models.notification_model import Notification
from core.models.saved_newsletter_model import SavedNewsletter
from core.models.check_compliance_chat_models import (
    CheckComplianceAttachment,
    CheckComplianceConversation,
    CheckComplianceMessage,
)
from core.models.stored_chat_models import StoredChatMessage, StoredChatSession
from core.models.perplexity_models import PerplexityConversation, PerplexityMessage
from core.models.quickdoc_model import GeneratedDocument
# Register your models here.
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'vat_number', 'company_type', 'status', 'capital')
    search_fields = ('name', 'vat_number')
    list_filter = ('company_type', 'status')

@admin.register(Officer)
class OfficerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'role', 'company', 'appointed_date', 'expiry_date')
    search_fields = ('name',)
    list_filter = ('role', 'company')

@admin.register(Shareholder)
class ShareholderAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'quota_percentage', 'company')
    search_fields = ('name',)
    list_filter = ('company',)

@admin.register(Deadline)
class DeadlineAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'company', 'due_date', 'completed', 'category')
    search_fields = ('title',)
    list_filter = ('company', 'completed', 'category')


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


@admin.register(CompanyDocumentLayout)
class CompanyDocumentLayoutAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'document_title', 'created_at', 'updated_at')
    search_fields = ('name', 'document_title')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'company',
        'tool',
        'sub_tool',
        'quantity',
        'occurred_at',
    )
    list_filter = ('tool', 'sub_tool', 'occurred_at')
    search_fields = ('user__email', 'company__name')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'occurred_at'


@admin.register(VeraUsageRecord)
class VeraUsageRecordAdmin(admin.ModelAdmin):
    list_display = (
        'date',
        'provider',
        'model',
        'cost_eur',
        'input_tokens',
        'output_tokens',
        'total_tokens',
        'request_count',
        'updated_at',
    )
    list_filter = ('provider', 'date', 'model')
    search_fields = ('model',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'date'
    ordering = ('-date', 'provider', 'model')


@admin.register(ComplianceLog)
class ComplianceLogAdmin(admin.ModelAdmin):
    list_display = (
        'data_rilevazione',
        'tipo_evento',
        'normativa',
        'autorita',
        'tag',
        'created_at',
    )
    list_filter = ('tipo_evento', 'autorita', 'tag', 'data_rilevazione')
    search_fields = ('normativa', 'autorita', 'riassunto_modifica')
    readonly_fields = ('id', 'raw_payload', 'created_at')
    date_hierarchy = 'data_rilevazione'
    ordering = ('-data_rilevazione', '-created_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'created_at',
        'notification_type',
        'title',
        'is_read',
        'reference_type',
        'reference_id',
        'read_at',
    )
    list_filter = ('notification_type', 'is_read', 'reference_type', 'created_at')
    search_fields = ('title', 'body', 'reference_id', 'reference_type')
    readonly_fields = ('id', 'created_at', 'read_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    actions = ('mark_as_read', 'mark_as_unread')

    @admin.action(description='Mark selected notifications as read')
    def mark_as_read(self, request, queryset):
        from django.utils import timezone

        queryset.update(is_read=True, read_at=timezone.now())

    @admin.action(description='Mark selected notifications as unread')
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False, read_at=None)


@admin.register(SavedNewsletter)
class SavedNewsletterAdmin(admin.ModelAdmin):
    list_display = (
        'created_at',
        'title',
        'newsletter_type',
        'source',
        'generated_at',
    )
    list_filter = ('newsletter_type', 'source', 'created_at', 'generated_at')
    search_fields = ('title', 'content')
    readonly_fields = ('id', 'metadata', 'created_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


class CheckComplianceMessageInline(admin.TabularInline):
    model = CheckComplianceMessage
    extra = 0
    readonly_fields = ('id', 'role', 'content', 'provider_payload', 'created_at')
    can_delete = False
    ordering = ('created_at',)


class CheckComplianceAttachmentInline(admin.TabularInline):
    model = CheckComplianceAttachment
    extra = 0
    readonly_fields = (
        'id',
        'message',
        'bucket',
        's3_key',
        'filename',
        'content_type',
        'size',
        'version_id',
        'created_at',
    )
    can_delete = False
    ordering = ('created_at',)


@admin.register(CheckComplianceConversation)
class CheckComplianceConversationAdmin(admin.ModelAdmin):
    list_display = ('updated_at', 'title', 'user', 'vera_session_id', 'is_saved', 'created_at')
    list_filter = ('is_saved', 'created_at', 'updated_at')
    search_fields = ('title', 'vera_session_id', 'user__email', 'user__username')
    readonly_fields = ('id', 'created_at', 'updated_at', 'metadata')
    date_hierarchy = 'updated_at'
    ordering = ('-updated_at',)
    inlines = [CheckComplianceMessageInline, CheckComplianceAttachmentInline]


@admin.register(CheckComplianceMessage)
class CheckComplianceMessageAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'conversation', 'role')
    list_filter = ('role', 'created_at')
    search_fields = ('content', 'conversation__title', 'conversation__vera_session_id')
    readonly_fields = ('id', 'provider_payload', 'created_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


@admin.register(CheckComplianceAttachment)
class CheckComplianceAttachmentAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'filename', 'conversation', 'content_type', 'size', 'bucket')
    list_filter = ('content_type', 'bucket', 'created_at')
    search_fields = ('filename', 's3_key', 'bucket', 'conversation__title')
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


class StoredChatMessageInline(admin.TabularInline):
    model = StoredChatMessage
    extra = 0
    readonly_fields = ('role', 'content', 'provider_payload', 'created_at')
    can_delete = False
    ordering = ('created_at',)


@admin.register(StoredChatSession)
class StoredChatSessionAdmin(admin.ModelAdmin):
    list_display = ('updated_at', 'title', 'provider', 'user', 'display_model', 'is_saved')
    list_filter = ('provider', 'is_saved', 'created_at', 'updated_at')
    search_fields = ('title', 'display_model', 'external_conversation_id', 'user__email', 'user__username')
    readonly_fields = ('id', 'metadata', 'created_at', 'updated_at')
    date_hierarchy = 'updated_at'
    ordering = ('-updated_at',)
    inlines = [StoredChatMessageInline]


@admin.register(StoredChatMessage)
class StoredChatMessageAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'session', 'role')
    list_filter = ('role', 'created_at')
    search_fields = ('session__title', 'session__external_conversation_id')
    readonly_fields = ('content', 'provider_payload', 'created_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


class PerplexityMessageInline(admin.TabularInline):
    model = PerplexityMessage
    extra = 0
    readonly_fields = ('role', 'content', 'included_in_summary', 'created_at')
    can_delete = False
    ordering = ('created_at',)


@admin.register(PerplexityConversation)
class PerplexityConversationAdmin(admin.ModelAdmin):
    list_display = ('updated_at', 'conversation_id', 'title', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('conversation_id', 'title', 'memory_summary')
    readonly_fields = ('conversation_id', 'created_at', 'updated_at')
    date_hierarchy = 'updated_at'
    ordering = ('-updated_at',)
    inlines = [PerplexityMessageInline]


@admin.register(PerplexityMessage)
class PerplexityMessageAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'conversation', 'role', 'included_in_summary')
    list_filter = ('role', 'included_in_summary', 'created_at')
    search_fields = ('conversation__conversation_id', 'conversation__title')
    readonly_fields = ('content', 'created_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


@admin.register(GeneratedDocument)
class GeneratedDocumentAdmin(admin.ModelAdmin):
    list_display = ('date', 'name', 'doc_format', 'language', 'pdf_file', 'word_file')
    list_filter = ('doc_format', 'language', 'date')
    search_fields = ('name', 'text')
    readonly_fields = ('date',)
    date_hierarchy = 'date'
    ordering = ('-date', 'name')
