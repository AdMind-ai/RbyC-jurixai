from rest_framework import serializers


class ExtractedContentSerializer(serializers.Serializer):
    document = serializers.CharField()
    content = serializers.CharField()
