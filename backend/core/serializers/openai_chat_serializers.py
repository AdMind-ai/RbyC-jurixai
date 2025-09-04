from rest_framework import serializers
from core.models.openai_chat_models import ChatMessage, ChatConversation


class MessageSerializer(serializers.ModelSerializer):
    conversation = serializers.PrimaryKeyRelatedField(
        queryset=ChatConversation.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = ChatMessage
        fields = [
            'id', 'conversation', 'content', 'citations',
            'file',
            'created_at',
            'is_user'
        ]
        read_only_fields = ['created_at']


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatConversation
        fields = ['id', 'name', 'created_at', 'messages']
        read_only_fields = ['id', 'created_at']

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Chat name cannot be empty.")
        return value

    def create(self, validated_data):
        messages_data = validated_data.pop('messages', [])
        conversation = ChatConversation.objects.create(**validated_data)
        print("Serializer: ", message_data, conversation)

        for message_data in messages_data:
            ChatMessage.objects.create(
                conversation=conversation, **message_data)

        return conversation

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.save()
        return instance
