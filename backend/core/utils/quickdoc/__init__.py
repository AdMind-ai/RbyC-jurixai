# core/views/__init__.py
from .create_pdf import create_pdf_with_template, create_pdf_for_verbale_cda
from .create_word import create_word_with_template, create_word_for_verbale_cda
from .assistant import generate_doc_with_assistant
from core.utils.storage import upload_bytes_to_storage as upload_to_storage

__all__ = [
    'create_pdf_with_template',
    'create_pdf_for_verbale_cda',
    'create_word_with_template',
    'create_word_for_verbale_cda',
    'generate_doc_with_assistant',
    'upload_to_storage',
]
