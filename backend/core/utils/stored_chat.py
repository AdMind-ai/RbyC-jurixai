from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

from core.models import StoredChatMessage, StoredChatSession

ContentBlock = Dict[str, Any]
ContentInput = Union[str, ContentBlock, Sequence[ContentBlock]]


def _normalize_content(content: ContentInput) -> List[ContentBlock]:
    if isinstance(content, list):
        return content
    if isinstance(content, dict):
        return [content]
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if content is None:
        return []
    return [{"type": "text", "text": str(content)}]


def get_or_create_stored_session(
    *,
    user: Any,
    provider: str,
    external_conversation_id: Optional[str],
    display_model: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    title: Optional[str] = None,
) -> Optional[StoredChatSession]:
    if not user or not getattr(user, "is_authenticated", False):
        return None

    defaults: Dict[str, Any] = {
        "display_model": display_model or "",
        "metadata": metadata or {},
        "title": title or "New Chat",
    }

    session, _created = StoredChatSession.objects.get_or_create(
        user=user,
        provider=provider,
        external_conversation_id=external_conversation_id,
        defaults=defaults,
    )

    updated_fields: List[str] = []

    if display_model and session.display_model != display_model:
        session.display_model = display_model
        updated_fields.append("display_model")

    if metadata:
        merged = {**session.metadata, **metadata}
        if merged != session.metadata:
            session.metadata = merged
            updated_fields.append("metadata")

    if title and session.title != title:
        session.title = title
        updated_fields.append("title")

    if updated_fields:
        session.save(update_fields=updated_fields + ["updated_at"])

    return session


def append_stored_message(
    *,
    session: Optional[StoredChatSession],
    role: str,
    content: ContentInput,
    provider_payload: Optional[Dict[str, Any]] = None,
) -> Optional[StoredChatMessage]:
    if session is None:
        return None

    normalized = _normalize_content(content)
    return StoredChatMessage.objects.create(
        session=session,
        role=role,
        content=normalized,
        provider_payload=provider_payload,
    )


__all__ = [
    "append_stored_message",
    "get_or_create_stored_session",
]
