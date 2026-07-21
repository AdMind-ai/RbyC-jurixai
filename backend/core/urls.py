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
    path('openai/segreteria/document-generator/', OpenAIDocumentGeneratorView.as_view(), name='openai-segreteria-document-generator'),
    
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
    path('check-compliance/chat/', CheckComplianceChatView.as_view(),
         name='check-compliance-chat'),
    path('check-compliance/chat/attachments/', CheckComplianceChatAttachmentUploadView.as_view(),
         name='check-compliance-chat-attachments'),
    path('check-compliance/chat/conversations/', CheckComplianceConversationListCreateView.as_view(),
         name='check-compliance-chat-conversations'),
    path('check-compliance/chat/conversations/<uuid:conversation_id>/', CheckComplianceConversationDetailView.as_view(),
         name='check-compliance-chat-conversation-detail'),
    path('check-compliance/documents/', CheckComplianceDocumentListView.as_view(),
         name='check-compliance-documents-list'),
    path('check-compliance/documents/upload/', CheckComplianceDocumentUploadView.as_view(),
         name='check-compliance-documents-upload'),
    path('check-compliance/documents/download/', CheckComplianceDocumentDownloadView.as_view(),
         name='check-compliance-documents-download'),
    path('check-compliance/documents/delete/', CheckComplianceDocumentDeleteView.as_view(),
         name='check-compliance-documents-delete'),
    path('check-compliance/documents/permanent-delete/', CheckComplianceDocumentPermanentDeleteView.as_view(),
         name='check-compliance-documents-permanent-delete'),
    path('check-compliance/documents/restore/', CheckComplianceDocumentRestoreView.as_view(),
         name='check-compliance-documents-restore'),
    path('openai/check-compliance/analyze/', CheckComplianceAnalyzeView.as_view(),
         name='openai-check-compliance-analyze'),
    path('check-compliance', CheckComplianceView.as_view(),
         name='check-compliance'),
    path('check-compliance/logs/', ComplianceLogListView.as_view(),
         name='check-compliance-logs'),
    path('check-compliance/logs/<uuid:pk>/', ComplianceLogDetailView.as_view(),
         name='check-compliance-log-detail'),
    path('vera/log/', VeraComplianceLogIngestView.as_view(),
         name='vera-log-ingest'),
    path('vera/newsletter/', VeraNewsletterDeliveryView.as_view(),
         name='vera-newsletter-delivery'),

    # Newsletter & PILL Formativo
    path('newsletter/chat/', NewsletterChatView.as_view(), name='newsletter-chat'),
    path('newsletter/saved/', SavedNewsletterListCreateView.as_view(), name='newsletter-saved-list'),
    path('newsletter/saved/<uuid:pk>/', SavedNewsletterDetailView.as_view(), name='newsletter-saved-detail'),
    path('newsletter/ingest/', VeraNewsletterIngestView.as_view(), name='newsletter-vera-ingest'),

    # Notifications
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/unread-count/', NotificationUnreadCountView.as_view(), name='notification-unread-count'),
    path('notifications/read-all/', NotificationReadAllView.as_view(), name='notification-read-all'),
    path('notifications/<uuid:pk>/read/', NotificationReadView.as_view(), name='notification-read'),

    # Vera usage tracking
    path('vera/usage/', VeraUsageIngestView.as_view(), name='vera-usage-ingest'),
    path('vera/usage/daily/', VeraUsageDailyView.as_view(), name='vera-usage-daily'),
    path('vera/usage/raw/', VeraUsageRawListView.as_view(), name='vera-usage-raw'),

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
