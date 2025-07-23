from django.contrib import admin
from core.models.openai_chat_models import ChatConversation, ChatMessage
from core.models.company_info import CompanyInfo, CEO, CompetitorInfo
# Register your models here.


class ChatMessageInline(admin.StackedInline):
    model = ChatMessage
    extra = 0


@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'created_at')
    list_filter = ('created_at', 'name')
    inlines = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'content', 'is_user', 'created_at')
    list_filter = ('created_at', 'is_user')
    search_fields = ('content',)


class CompetitorInline(admin.TabularInline):
    model = CompetitorInfo
    extra = 0


class CEOInline(admin.TabularInline):
    model = CEO
    extra = 0


@admin.register(CompanyInfo)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('long_name', 'stock_symbol', 'sector', 'country')
    inlines = [CompetitorInline, CEOInline]
