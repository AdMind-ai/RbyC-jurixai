from rest_framework.views import APIView
from rest_framework.response import Response
from core.utils.openai_client import client
from core.models.assistant_thread_model import AssistantThread
from rest_framework import status, permissions
from rest_framework import serializers
from rest_framework.permissions import AllowAny


class AssistantThreadSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssistantThread
        fields = ['thread_id', 'created_at', 'active']


class ThreadsView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # 1. Cria o thread na OpenAI
        thread = client.beta.threads.create()
        # 2. Salva localmente
        AssistantThread.objects.create(
            thread_id=thread.id,
            active=False,
        )
        return Response({"threadId": thread.id}, status=status.HTTP_201_CREATED)

    def get(self, request):
        # Filtra threads ativas, só do usuário autenticado
        threads = AssistantThread.objects.filter(
            active=True).order_by("-created_at")
        serializer = AssistantThreadSerializer(threads, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, thread_id):
        try:
            thread = AssistantThread.objects.get(
                thread_id=thread_id)
            thread.active = False
            thread.save()
            client.beta.threads.delete(thread_id)
            return Response(status=204)
        except AssistantThread.DoesNotExist:
            return Response({"error": "Thread not found"}, status=404)
