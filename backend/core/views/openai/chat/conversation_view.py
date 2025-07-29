from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets, permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser

from core.models.openai_chat_models import ChatConversation, ChatMessage
from core.serializers.openai_chat_serializers import ConversationSerializer


class OpenAIConversationViewSet(viewsets.ModelViewSet):
    queryset = ChatConversation.objects.all()
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [JWTAuthentication]
    parser_classes = [FormParser, MultiPartParser, JSONParser]

    def get_queryset(self):
        user = self.request.user
        only_saved = self.request.query_params.get(
            "only_saved", "true").lower() == "true"
        # Por padrão só retorna conversas salvas (is_new=False)
        queryset = ChatConversation.objects.filter(user=user)
        if only_saved:
            queryset = queryset.filter(is_new=False)
        return queryset

    def create(self, request, *args, **kwargs):
        user = request.user
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        messages = request.data.get('messages')
        conversation_name = request.data.get('name')

        conversation = ChatConversation.objects.create(
            user=user,
            name=conversation_name
        )

        for message in messages:
            ChatMessage.objects.create(
                conversation=conversation,
                content=message['content'],
                # citations=message.get('citations', []),
                # file=None,
                is_user=message['is_user']
            )

        data = serializer.data
        data['id'] = conversation.id

        return Response(data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        print(
            f"Deleting chat with ID: {instance.id} and Name: {instance.name}")
        instance.delete()

    @action(detail=True, methods=['post'])
    def add_message(self, request, pk=None):
        conversation = self.get_object()
        data = request.data.copy()
        data['conversation'] = conversation.id

        serializer = MessageSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)
