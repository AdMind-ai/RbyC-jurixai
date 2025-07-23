from rest_framework import serializers
from core.models.core_model import CoreModel


class CoreSerializer(serializers.ModelSerializer):
    """
    Serializador para o CoreModel.
    """
    class Meta:
        model = CoreModel
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']
