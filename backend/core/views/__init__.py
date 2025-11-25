# core/views/__init__.py
from .deepl import DeeplTranslateFileView
from .deepl import DeeplTranslateTextView

from .openai import (OpenAIConversationViewSet,
                     OpenAISendMessageView,
                     AssistantStreamingView,
                     ThreadsView,
                     SaveConversationView,
                     ConversationForChatView)

from .extract_content_view import ExtractContentView
from .quickdoc_view import QuickDocGenerateView
from .check_compliance_view import CheckComplianceView
from .segretaria_societaria.deadline_view import DeadlineListCreateView, DeadlineUpdateView
from .segretaria_societaria.company_view import CompanyListCreateView, CompanyUpdateView
from .segretaria_societaria.officer_view import OfficerListCreateView, OfficerUpdateView
from .segretaria_societaria.shareholder_view import ShareholderListCreateView, ShareholderUpdateView

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
]
