from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from integrations.authentication import APIKeyAuthentication
from integrations.permissions import HasValidAPIKey
from core.utils.openai_client import client
from rest_framework import status


@extend_schema(summary="Create OpenAI conversation for integrations")
class ConversationForChatView(APIView):
    """Expose endpoint to create an OpenAI conversation for integration clients.

    Protected by API key auth so external systems can obtain a `conversation_id`
    and pass it to the ricerca-documentale POST to keep the same conversation.
    """

    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasValidAPIKey]

    def post(self, request, *args, **kwargs):
        try:
            conversation = client.conversations.create()
            return Response({"conversation_id": conversation.id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": "failed to create conversation"}, status=status.HTTP_502_BAD_GATEWAY)
