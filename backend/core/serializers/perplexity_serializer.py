from rest_framework import serializers


class PerplexityRequestSerializer(serializers.Serializer):
    message = serializers.CharField(required=True)
