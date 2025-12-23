from django.urls import path
from integrations.views.health import HealthCheckView
from integrations.views.ricerca_documentale import RicercaDocumentaleView
from integrations.views.conversation import ConversationForChatView

app_name = "integrations_v1"

urlpatterns = [
    path("ricerca-documentale/", RicercaDocumentaleView.as_view(), name="ricerca_documentale"),
    path("openai/conversation/", ConversationForChatView.as_view(), name="conversation_create"),
]
