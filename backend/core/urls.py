# core/urls.py PerplexityCEONewsView
from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'openai/chat', OpenAIConversationViewSet,
                basename='openai-chat-conversation')

urlpatterns = [
    path('company-info/',
         CompanyInfoViewAdm.as_view(), name='company-info-adm'),
    path('deepl/file/', DeeplTranslateFileView.as_view(), name='translate-file'),
    path('deepl/text/', DeeplTranslateTextView.as_view(), name='translate-text'),
    # Chat
    path('openai/chat/send-message/', OpenAISendMessageView.as_view(),
         name='openai-chat-send-message'),
    path('openai/assistant/send-message/', OpenAISendAssistantMessageView.as_view(),
         name='openai-assistant-send-message'),
    path('extract-content/file/', ExtractContentView.as_view(),
         name='extract-file-content'),
    path('quickdoc/generate/', QuickDocGenerateView.as_view(),
         name='quickdoc-generate'),

]

urlpatterns += router.urls
