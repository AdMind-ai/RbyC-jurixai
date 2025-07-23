from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework import status, viewsets, generics

from .serializers import (CustomUserSerializer,
                          CustomTokenObtainPairSerializer, RegisterSerializer)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet to list users.
    """
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAdminUser]

    def create(self, request, *args, **kwargs):
        return Response({"detail": "Creating users is not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


class RegisterView(generics.CreateAPIView):
    """
    Endpoint to register new users.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
