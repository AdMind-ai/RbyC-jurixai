from rest_framework import serializers

class OpenAIAssistantMessageSerializer(serializers.Serializer):
    text = serializers.CharField(required=False)
    file = serializers.FileField(required=False)
    response = serializers.CharField(read_only = True)  