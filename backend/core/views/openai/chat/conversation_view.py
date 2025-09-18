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
        is_chat_rag = self.request.query_params.get("is_chat_rag")
        # Por padrão só retorna conversas salvas (is_new=False)
        queryset = ChatConversation.objects.filter(user=user)
        
        if only_saved:
            queryset = queryset.filter(is_new=False)
        
        if is_chat_rag is not None:
            queryset = queryset.filter(is_chat_rag=(is_chat_rag.lower() == "true"))
        else:
            queryset = queryset.filter(is_chat_rag=False)
            
        return queryset
    
    def get_object(self):
        """
        Garantir que o detail view sempre retorna a conversa do usuário,
        sem filtrar por is_chat_rag.
        """
        return ChatConversation.objects.get(
            pk=self.kwargs['pk'],
            user=self.request.user
        )

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
                citations=message.get('citations', []),
                file=None,
                is_user=message['is_user']
            )

        serializer = self.serializer_class(conversation)  # ✅ serialize instance
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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

from openai import OpenAI
from django.conf import settings
client = OpenAI(api_key=settings.OPENAI_KEY)

class ConversationForChatView(APIView):
    
    permission_classes = [permissions.AllowAny]
    """ View que cria uma conversa para o chat """
    
    def post(self, request, *args, **kwargs):
        # Cria uma conversa vazia
        conversation = client.conversations.create()

        return Response({
            "conversation_id": conversation.id
        }, status=201)
