from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class PasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, required=True)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'is_company_admin', 'first_name', 'last_name']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            is_company_admin=validated_data.get('is_company_admin', False),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )
        return user


class CustomUserSerializer(serializers.ModelSerializer):
    createdAt = serializers.DateTimeField(source='date_joined', read_only=True)
    modifiedAt = serializers.DateTimeField(
        source='modified_at', read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "email", "is_company_admin", "createdAt", "modifiedAt"
        ]


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Personaliza o token para incluir mais informações do usuário"""

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data.update({
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_company_admin": getattr(user, "is_company_admin", False),
        })
        return data


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(required=False, allow_blank=True)
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        # Optionally, add additional password validation here
        if not value:
            raise serializers.ValidationError('Password cannot be empty')
        return value
