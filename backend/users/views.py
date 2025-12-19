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
from core.utils.mailapi import send_template_email
from .serializers import PasswordResetSerializer, PasswordResetConfirmSerializer
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.core.cache import cache

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

    def get_queryset(self):
        user = self.request.user
        qs = User.objects.all()
        if not user.is_staff:
            qs = qs.filter(is_staff=False)
        return qs

    def get_permissions(self):
        if self.action in ['create', 'destroy', 'update', 'partial_update']:
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


class PasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        users = User.objects.filter(email__iexact=email)
        frontend_base = settings.FRONTEND_URL

        # If no users found, report failure (front will show toast)
        if not users.exists():
            return Response({"detail": "Non siamo riusciti a inviare l'email per reimpostare la password. Indirizzo email non valido."}, status=400)

        sent_any = False
        errors = []

        for user in users:
            token = PasswordResetTokenGenerator().make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            reset_link = f"{frontend_base}/reset-password?uid={uid}&token={token}"

            try:
                result = send_template_email(
                    to_email=user.email,
                    subject="RbyC - Password Reset Request",
                    template_id="ai_1766037282924",
                    variables={
                        "resetLink": reset_link,
                    },
                )
            except Exception as exc:
                # network or unexpected error
                errors.append(str(exc))
                result = {"ok": False, "status_code": None, "text": str(exc)}

            # Inspect the mail API response status
            status_code = result.get("status_code")
            text = result.get("text")
            ok = bool(result.get("ok"))

            if ok:
                sent_any = True
                # store a cache key so we can enforce expiration independent of token internals
                try:
                    timeout = 600  # Five minutes
                    cache_key = f"pwdreset:{uid}:{token}"
                    cache.set(cache_key, True, timeout=timeout)
                except Exception:
                    # if cache unavailable, continue without cache enforcement
                    pass
            else:
                errors.append(f"mailapi_status={status_code} text={text}")

        if sent_any:
            return Response({"detail": f"È stato inviato un link per il reset della password a {email}."}, status=200)
        else:
            return Response({"detail": "Non è stato possibile inviare l'email per il reset della password."}, status=500)

class PasswordResetConfirmView(APIView):
    """Endpoint to confirm a password reset using uid and token."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uid = serializer.validated_data.get('uid')
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        if not uid:
            return Response({'detail': 'UID is required'}, status=400)

        try:
            uid_decoded = force_str(urlsafe_base64_decode(uid))
            user = get_object_or_404(User, pk=uid_decoded)
        except Exception:
            return Response({'detail': 'Invalid uid'}, status=400)

        if not PasswordResetTokenGenerator().check_token(user, token):
            return Response({'detail': 'Invalid or expired token'}, status=400)
        # additionally check our cache-based expiration (if set)
        try:
            timeout = getattr(settings, 'PASSWORD_RESET_TIMEOUT', 3600)
            cache_key = f"pwdreset:{uid}:{token}"
            if not cache.get(cache_key):
                return Response({'detail': 'Token scaduto o non valido'}, status=400)
        except Exception:
            # if cache fail, fall back to token check result
            pass

        # remove cache key after successful use
        try:
            cache.delete(cache_key)
        except Exception:
            pass
        user.set_password(new_password)
        user.save()
        return Response({'detail': 'Password reset successful'})
