# core/urls.py PerplexityCEONewsView
from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'openai/chat', OpenAIConversationViewSet,
                basename='openai-chat-conversation')

urlpatterns = [
    path('deepl/file/', DeeplTranslateFileView.as_view(), name='translate-file'),
    path('deepl/text/', DeeplTranslateTextView.as_view(), name='translate-text'),
    # Chat
    path('openai/chat/send-message/', OpenAISendMessageView.as_view(),
         name='openai-chat-send-message'),
    # QuickDoc
    path('extract-content/file/', ExtractContentView.as_view(),
         name='extract-file-content'),
    path('quickdoc/generate/', QuickDocGenerateView.as_view(),
         name='quickdoc-generate'),
    # Chat with assistant
    path('openai/chat/assistant/send-message',
         AssistantStreamingView.as_view(), name='openai-chat-assistant-send-message'),
    path('openai/chat/assistant/thread', ThreadsView.as_view(),
         name='openai-chat-assistant-thread'),
    path('openai/chat/assistant/save-conversation', SaveConversationView.as_view(),
         name='openai-chat-assistant-save-conversation'),
    # Law consultant
    path('openai/chat/assistant/law-consultant', AssistantLawConsultantView.as_view(),
         name='openai-chat-assistant-law-consultant')
]

urlpatterns += router.urls
