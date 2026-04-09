# core/views/__init__.py
from .deepl import DeeplTranslateFileView
from .deepl import DeeplTranslateTextView

from .openai import (OpenAIConversationViewSet,
                     OpenAISendMessageView,
                     AssistantStreamingView,
                     ThreadsView,
                     SaveConversationView,
                     ConversationForChatView)

from .company_document_layout_view import CompanyDocumentLayoutView, CompanyDocumentLayoutDetailView
from .draft_document.generate_document_view import DraftDocumentView, DraftDocumentFileView
from .extract_content_view import ExtractContentView
from .quickdoc_view import QuickDocGenerateView
from .check_compliance_view import CheckComplianceView
from .s3_upload_view import S3UploadView, S3TokenView
from .segretaria_societaria.deadline_view import DeadlineListCreateView, DeadlineUpdateView
from .segretaria_societaria.company_view import CompanyListCreateView, CompanyUpdateView, CompanyLetterheadProxyView, GenerateDocumentPDFView
from .segretaria_societaria.officer_view import OfficerListCreateView, OfficerUpdateView
from .segretaria_societaria.shareholder_view import ShareholderListCreateView, ShareholderUpdateView
from .perplexity.chat_assistant import PerplexityChatAssistant
from .stored_chat_session_view import (
    StoredChatSessionSaveView,
    StoredChatSessionListView,
    StoredChatSessionDetailView,
)
from .usage_view import UsageManualRecordView, UsageMonthListView, UsageReportView
from .costs_view import CostAggregatorView

__all__ = [
    'DeeplTranslateFileView',
    'DeeplTranslateTextView',
    'OpenAIConversationViewSet',
    'OpenAISendMessageView',
    'ExtractContentView',
    'QuickDocGenerateView',
    'AssistantStreamingView',
    'ThreadsView',
    'SaveConversationView',
    'ConversationForChatView',
    'CheckComplianceView',
    'DeadlineListCreateView',
    'DeadlineUpdateView',
    'CompanyListCreateView',
    'CompanyUpdateView',
    'OfficerListCreateView',
    'OfficerUpdateView',
    'ShareholderListCreateView',
    'ShareholderUpdateView',
    'CompanyLetterheadProxyView',
    'GenerateDocumentPDFView',
    'DraftDocumentView',
    'DraftDocumentFileView',
    'CompanyDocumentLayoutView',
    'CompanyDocumentLayoutDetailView',
    'S3UploadView',
    'S3TokenView',
    'PerplexityChatAssistant',
    'StoredChatSessionSaveView',
    'StoredChatSessionListView',
    'StoredChatSessionDetailView',
    'UsageReportView',
    'UsageMonthListView',
    'UsageManualRecordView',
    'CostAggregatorView',
]
