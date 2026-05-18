from django.urls import path
from integrations.views.health import HealthCheckView
from integrations.views.ricerca_documentale import RicercaDocumentaleView
from integrations.views.conversation import ConversationForChatView
from integrations.views.document_index import (
    InternalDocumentIndexContentView,
    InternalDocumentIndexView,
)

app_name = "integrations_v1"

urlpatterns = [
    path("ricerca-documentale/", RicercaDocumentaleView.as_view(), name="ricerca_documentale"),
    path("openai/conversation/", ConversationForChatView.as_view(), name="conversation_create"),
    path("internal/document-index/", InternalDocumentIndexView.as_view(), name="internal_document_index"),
    path("internal/document-index-content/", InternalDocumentIndexContentView.as_view(), name="internal_document_index_content"),
]
