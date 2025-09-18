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
    thread_id = serializers.SerializerMethodField()

    class Meta:
        model = ChatConversation
        fields = ['id', 'thread_id', 'name', 'created_at', 'messages']
        read_only_fields = ['id', 'created_at']

    def get_thread_id(self, obj):
        # Pega o primeiro AssistantThread ativo vinculado
        thread = obj.threads.filter(active=True).first()
        return thread.thread_id if thread else None

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Chat name cannot be empty.")
        return value

    def create(self, validated_data):
        messages_data = validated_data.pop('messages', [])
        conversation = ChatConversation.objects.create(**validated_data)

        for message_data in messages_data:
            ChatMessage.objects.create(conversation=conversation, **message_data)

        return conversation

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        if instance.is_new:
            instance.is_new = False
        if 'is_chat_rag' in validated_data:
            instance.is_chat_rag = validated_data.get('is_chat_rag')
        instance.save()
        return instance
