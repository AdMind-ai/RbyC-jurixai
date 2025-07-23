from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.urls import reverse
from core.models.core_model import CoreModel
from core.serializers.core_serializer import CoreSerializer


class CoreViewSet(viewsets.ModelViewSet):
    """
    ViewSet to manage application data.
    """
    queryset = CoreModel.objects.all()
    serializer_class = CoreSerializer
    permission_classes = [permissions.IsAuthenticated]


class APIRootView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user_id = request.user.id
        return Response({
            # "main": request.build_absolute_uri(reverse("api-root")),
            "company": request.build_absolute_uri(reverse("company-info-adm")),
            "file_extractor": request.build_absolute_uri(reverse("extract-file-content")),
            "quickdoc-generate": request.build_absolute_uri(reverse("quickdoc-generate")),
            "users": {
                "token_obtain": request.build_absolute_uri(reverse("token_obtain_pair")),
                "token_refresh": request.build_absolute_uri(reverse("token_refresh")),
                "user_register": request.build_absolute_uri(reverse("register_user")),
                "users_list": request.build_absolute_uri(reverse("users-list")),
                "user_detail_current": request.build_absolute_uri(reverse("users-detail", kwargs={'pk': user_id})),
            },
            "core": {
                "deepl": {
                    "file": request.build_absolute_uri(reverse("translate-file")),
                    "text": request.build_absolute_uri(reverse("translate-text")),
                },
                "openai": {
                    "chat-conversation": request.build_absolute_uri(reverse("openai-chat-conversation-list")),
                    "chat-send-message": request.build_absolute_uri(reverse("openai-chat-send-message")),
                },
            }
        })
