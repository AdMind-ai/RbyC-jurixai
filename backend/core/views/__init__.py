# core/views/__init__.py
from .deepl import DeeplTranslateFileView
from .deepl import DeeplTranslateTextView

from .openai import (OpenAIConversationViewSet,
                     OpenAISendMessageView,
                     AssistantStreamingView,
                     ThreadsView,
                     SaveConversationView)

from .extract_content_view import ExtractContentView
from .quickdoc_view import QuickDocGenerateView

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
    # 'AssistantLawConsultantView'
]
