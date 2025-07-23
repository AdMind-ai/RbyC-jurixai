# core/views/__init__.py
from .create_pdf import create_pdf_with_header_footer
from .create_word import create_word_with_header_footer
from .assistant import generate_doc_with_assistant
from .upload_to_blob_storage import upload_to_blob_storage

__all__ = [
    'create_pdf_with_header_footer',
    'create_word_with_header_footer',
    'generate_doc_with_assistant',
    'upload_to_blob_storage'
]
