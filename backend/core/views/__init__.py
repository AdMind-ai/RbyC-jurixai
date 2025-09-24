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
    # 'AssistantLawConsultantView'
]
