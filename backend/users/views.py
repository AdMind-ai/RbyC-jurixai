from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework import status, viewsets, generics
from rest_framework.decorators import action

from .serializers import (
    CustomUserSerializer,
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    PasswordSerializer
)

User = get_user_model()


class IsCompanyAdmin(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and getattr(request.user, "is_company_admin", False)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return RegisterSerializer
        if self.action == 'set_password':
            return PasswordSerializer
        return CustomUserSerializer

    def perform_create(self, serializer):
        company = self.request.user.company
        serializer.context['company'] = self.request.user.company
        print(f"Company: {company}")
        serializer.save(company=company)

    def get_queryset(self):
        user = self.request.user
        return User.objects.filter(company=user.company)

    def get_permissions(self):
        if self.action in ['create', 'destroy', 'update']:
            return [IsCompanyAdmin()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path="set_password")
    def set_password(self, request, pk=None):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data['password'])
        user.save()
        return Response({'status': 'Password updated successfully'})


class RegisterView(generics.CreateAPIView):
    """
    Endpoint to register new users.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
