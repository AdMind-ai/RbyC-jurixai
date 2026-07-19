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
