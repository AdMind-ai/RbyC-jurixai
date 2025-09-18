from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from core.models.assistant_thread_model import AssistantThread
from rest_framework import serializers


class SaveConversationSerializer(serializers.Serializer):
    thread_id = serializers.CharField(required=True)
    name = serializers.CharField(required=True)


class SaveConversationView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SaveConversationSerializer

    def post(self, request):
        thread_id = request.data.get("thread_id")
        new_name = request.data.get("name")
        is_chat_rag = request.data.get("is_chat_rag")

        if not thread_id or not new_name:
            return Response({"error": "thread_id and name required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            assistant_thread = AssistantThread.objects.get(thread_id=thread_id)
            conversation = assistant_thread.conversation
            if not conversation:
                return Response({"error": "Thread is not yet linked to a conversation."}, status=400)

            conversation.is_new = False
            conversation.name = new_name
            if is_chat_rag:
                conversation.is_chat_rag = True
            conversation.save()
            return Response({"success": True}, status=200)
        except AssistantThread.DoesNotExist:
            return Response({"error": "Thread not found"}, status=404)
