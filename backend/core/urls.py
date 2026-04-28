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
    path('openai/chat/create-conversation/', ConversationForChatView.as_view(),
         name='openai-chat-create-conversation'),
    path('extract-content/file/', ExtractContentView.as_view(),
         name='extract-file-content'),

    # Company Document Layout (draft document)
    path('company/document-layout/', CompanyDocumentLayoutView.as_view(),
         name='company-document-layout'),
    path('company/document-layout/<int:pk>/', CompanyDocumentLayoutDetailView.as_view(),
         name='company-document-layout-detail'),

     # Usage report & metadata
     path('usage/report/', UsageReportView.as_view(), name='usage-report'),
     path('usage/months/', UsageMonthListView.as_view(), name='usage-months'),
     path('usage/manual/', UsageManualRecordView.as_view(), name='usage-manual'),
    
    # Draft document generation (OpenAI)
    path('openai/draft/generate/', DraftDocumentView.as_view(), name='draft-document'),
    path('openai/draft/export/', DraftDocumentFileView.as_view(), name='draft-document-file'),
    
    # Chat with assistant
    path('openai/chat/assistant/send-message',
         AssistantStreamingView.as_view(), name='openai-chat-assistant-send-message'),
    path('openai/chat/assistant/send-message-stream',
         AssistantDocumentSearchStreamView.as_view(), name='openai-chat-assistant-send-message-stream'),
    path('openai/chat/assistant/thread', ThreadsView.as_view(),
         name='openai-chat-assistant-thread'),
    path('openai/chat/assistant/save-conversation', SaveConversationView.as_view(),
         name='openai-chat-assistant-save-conversation'),
    path('chat/sessions/save', StoredChatSessionSaveView.as_view(),
         name='stored-chat-session-save'),
    path('chat/sessions/', StoredChatSessionListView.as_view(),
         name='stored-chat-session-list'),
    path('chat/sessions/<uuid:session_id>/', StoredChatSessionDetailView.as_view(),
         name='stored-chat-session-detail'),
    
     # Chat assistant with perplexity
     path('perplexity/chat/assistant', PerplexityChatAssistant.as_view(),
           name='perplexity-chat-assistant'),
   
    # Check Compliance
    path('openai/check-compliance/analyze/', CheckComplianceAnalyzeView.as_view(),
         name='openai-check-compliance-analyze'),
    path('check-compliance', CheckComplianceView.as_view(),
         name='check-compliance'),

    # Deadlines
    path('deadlines/', DeadlineListCreateView.as_view(), name='deadline-list-create'),
    path('deadlines/<int:pk>/', DeadlineUpdateView.as_view(), name='deadline-update'),
     # Company
     path('companies/', CompanyListCreateView.as_view(), name='company-list-create'),
     path('companies/<int:pk>/', CompanyUpdateView.as_view(), name='company-update'),
     path('companies/letterhead-proxy/', CompanyLetterheadProxyView.as_view(), name='company-letterhead-proxy'),
     path('documents/generate-pdf/', GenerateDocumentPDFView.as_view(), name='generate-document-pdf'),
     # Officer
     path('officers/', OfficerListCreateView.as_view(), name='officer-list-create'),
     path('officers/<int:pk>/', OfficerUpdateView.as_view(), name='officer-update'),
     # Shareholder
     path('shareholders/', ShareholderListCreateView.as_view(), name='shareholder-list-create'),
     path('shareholders/<int:pk>/', ShareholderUpdateView.as_view(), name='shareholder-update'),
     # S3 upload
     path('uploads/s3/token/', S3TokenView.as_view(), name='s3-upload-token'),
     path('uploads/s3/', S3UploadView.as_view(), name='s3-upload'),
]

urlpatterns += router.urls
