from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import (
    AssistantThread,
    PerplexityConversation,
    StoredChatMessage,
    StoredChatSession,
)


class StoredChatMessageInputSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["system", "user", "assistant", "ai"])
    content = serializers.JSONField()


class StoredChatSessionSaveSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=StoredChatSession.ProviderChoices.choices)
    session_id = serializers.UUIDField(required=False)
    conversation_id = serializers.CharField(required=False, allow_blank=True)
    title = serializers.CharField(max_length=255)
    display_model = serializers.CharField(required=False, allow_blank=True)
    messages = serializers.ListField(
        child=StoredChatMessageInputSerializer(), required=False, allow_empty=True
    )


class StoredChatSessionSaveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = StoredChatSessionSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        provider = data["provider"]
        session_id = data.get("session_id")
        conversation_id = data.get("conversation_id")
        title = data["title"]
        display_model = data.get("display_model", "")
        provided_messages = data.get("messages", [])

        user = request.user

        if provider == StoredChatSession.ProviderChoices.GPT:
            normalized_messages, metadata = self._fetch_gpt_history(
                user=user,
                conversation_id=conversation_id,
                fallback_messages=provided_messages,
            )
        elif provider == StoredChatSession.ProviderChoices.PERPLEXITY:
            normalized_messages, metadata = self._fetch_perplexity_history(
                conversation_id=conversation_id,
                fallback_messages=provided_messages,
            )
        else:  # gemini or any provider without backend history
            normalized_messages = self._normalize_from_payload(provided_messages)
            metadata = {}
            if not normalized_messages:
                raise ValidationError("messages são obrigatórias para este provedor.")

        session, created = self._resolve_session(
            user=user,
            provider=provider,
            session_id=session_id,
            conversation_id=conversation_id,
            title=title,
            display_model=display_model,
        )

        session.title = title
        session.display_model = display_model
        session.is_saved = True
        update_fields = ["title", "display_model", "is_saved", "updated_at"]

        if conversation_id and session.external_conversation_id != conversation_id:
            session.external_conversation_id = conversation_id
            update_fields.append("external_conversation_id")

        if metadata:
            merged = {**(session.metadata or {}), **metadata}
            session.metadata = merged
            update_fields.append("metadata")

        session.save(update_fields=update_fields)

        session.messages.all().delete()
        StoredChatMessage.objects.bulk_create(
            [
                StoredChatMessage(
                    session=session,
                    role=message["role"],
                    content=message["content"],
                )
                for message in normalized_messages
            ]
        )

        return Response(
            {
                "id": str(session.id),
                "provider": session.provider,
                "title": session.title,
                "display_model": session.display_model,
                "updated_at": session.updated_at,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def _resolve_session(
        self,
        *,
        user,
        provider: str,
        session_id: Optional[str],
        conversation_id: Optional[str],
        title: str,
        display_model: str,
    ) -> Tuple[StoredChatSession, bool]:
        if session_id:
            session = get_object_or_404(
                StoredChatSession,
                id=session_id,
                user=user,
            )
            return session, False

        if conversation_id:
            return StoredChatSession.objects.get_or_create(
                user=user,
                provider=provider,
                external_conversation_id=conversation_id,
                defaults={
                    "title": title,
                    "display_model": display_model,
                    "is_saved": True,
                },
            )

        session = StoredChatSession.objects.create(
            user=user,
            provider=provider,
            external_conversation_id=None,
            title=title,
            display_model=display_model,
            is_saved=True,
        )
        return session, True

    def _fetch_gpt_history(
        self,
        *,
        user,
        conversation_id: Optional[str],
        fallback_messages: List[Dict[str, Any]],
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        if not conversation_id:
            if fallback_messages:
                return self._normalize_from_payload(fallback_messages), {}
            raise ValidationError("conversation_id é obrigatório para salvar conversas GPT.")

        thread = (
            AssistantThread.objects.select_related("conversation", "conversation__user")
            .filter(thread_id=conversation_id, conversation__user=user)
            .first()
        )
        if not thread or not thread.conversation:
            if fallback_messages:
                return self._normalize_from_payload(fallback_messages), {}
            raise ValidationError("Conversa GPT não encontrada para este usuário.")

        normalized = [
            {
                "role": "user" if message.is_user else "assistant",
                "content": self._normalize_content(message.content or ""),
            }
            for message in thread.conversation.messages.order_by("created_at")
        ]
        return normalized, {"chat_conversation_id": str(thread.conversation.id)}

    def _fetch_perplexity_history(
        self,
        *,
        conversation_id: Optional[str],
        fallback_messages: List[Dict[str, Any]],
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        if not conversation_id:
            if fallback_messages:
                return self._normalize_from_payload(fallback_messages), {}
            raise ValidationError("conversation_id é obrigatório para salvar conversas Perplexity.")

        conversation = PerplexityConversation.objects.filter(
            conversation_id=conversation_id
        ).first()
        if not conversation:
            if fallback_messages:
                return self._normalize_from_payload(fallback_messages), {}
            raise ValidationError("Conversa Perplexity não encontrada.")

        normalized = [
            {
                "role": message.role,
                "content": self._normalize_content(message.content),
            }
            for message in conversation.messages.order_by("created_at")
        ]
        return normalized, {"memory_summary": conversation.memory_summary}

    def _normalize_from_payload(self, payload: List[Dict[str, Any]]):
        normalized: List[Dict[str, Any]] = []
        for entry in payload:
            role = entry.get("role")
            if role == "ai":
                role = "assistant"
            if role not in {"system", "user", "assistant"}:
                raise ValidationError("role inválido nas mensagens enviadas.")
            content = entry.get("content", "")
            normalized.append({
                "role": role,
                "content": self._normalize_content(content),
            })
        return normalized

    @staticmethod
    def _normalize_content(content: Any) -> List[Dict[str, Any]]:
        if isinstance(content, list):
            return content
        if isinstance(content, dict):
            return [content]
        if isinstance(content, str):
            return [{"type": "text", "text": content}]
        if content is None:
            return [{"type": "text", "text": ""}]
        return [{"type": "text", "text": str(content)}]


class StoredChatSessionListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        provider = request.query_params.get("provider")
        sessions = StoredChatSession.objects.filter(user=request.user, is_saved=True)
        if provider:
            sessions = sessions.filter(provider=provider)
        data = [
            {
                "id": str(session.id),
                "provider": session.provider,
                "title": session.title,
                "display_model": session.display_model,
                "external_conversation_id": session.external_conversation_id,
                "updated_at": session.updated_at,
            }
            for session in sessions.order_by("-updated_at")
        ]
        return Response(data)


class StoredChatSessionDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, session_id):
        session = get_object_or_404(
            StoredChatSession,
            id=session_id,
            user=request.user,
            is_saved=True,
        )
        messages = [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in session.messages.order_by("created_at")
        ]
        return Response(
            {
                "id": str(session.id),
                "provider": session.provider,
                "title": session.title,
                "display_model": session.display_model,
                "external_conversation_id": session.external_conversation_id,
                "metadata": session.metadata,
                "messages": messages,
            }
        )

    def delete(self, request, session_id):
        session = get_object_or_404(
            StoredChatSession,
            id=session_id,
            user=request.user,
        )
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
