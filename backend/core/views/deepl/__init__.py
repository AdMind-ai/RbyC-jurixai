# core/views/__init__.py
from .translate_file_view import DeeplTranslateFileView
from .translate_text_view import DeeplTranslateTextView


__all__ = [
    'DeeplTranslateFileView',
    'DeeplTranslateTextView',
]
