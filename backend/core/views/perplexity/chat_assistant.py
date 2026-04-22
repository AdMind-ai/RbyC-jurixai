import base64
from typing import List, Optional

from backend import settings
from billing.services.provider_usage_costs import ProviderUsageCostService
from core.models.usage import UsageSubTool, UsageTool
from core.services.usage_tracking import UsageTrackingService
from perplexity import Perplexity
from rest_framework.views import APIView
from django.http import StreamingHttpResponse

from core.models.perplexity_models import (
    PerplexityConversation,
    PerplexityMessage,
)

# Initialize the client (uses PERPLEXITY_API_KEY environment variable)
client = Perplexity(api_key=settings.PERPLEXITY_API_KEY)

def encode_uploaded_file(uploaded_file):
    """Return the raw base64 bytes (without prefix)."""
    file_data = uploaded_file.read()
    uploaded_file.seek(0)
    encoded = base64.b64encode(file_data).decode('utf-8')
    return encoded

class PerplexityChatAssistant(APIView):
    max_context_messages = getattr(settings, "PERPLEXITY_CONTEXT_MESSAGES", 12)

    def post(self, request, *args, **kwargs):
        user_input = request.data.get('input', '').strip()
        if not user_input:
            return StreamingHttpResponse("No input provided.", status=400)

        conversation_id = request.data.get('conversation_id') or request.query_params.get('conversation_id')
        conversation = self._get_or_create_conversation(conversation_id)

        # Collect every uploaded file and convert it to a data URL
        uploaded_files = request.FILES.getlist('file')
        file_contents = []
        for uploaded_file in uploaded_files:
            try:
                encoded_file = encode_uploaded_file(uploaded_file)
                file_contents.append({
                    "type": "file_url",
                    "file_url": {"url": encoded_file},
                    "file_name": uploaded_file.name or 'uploaded-file'
                })
            except Exception:
                continue

        user_message_content = [
            {
                "type": "text",
                "text": user_input
            },
            *file_contents
        ]

        messages_payload = []
        system_context = self._build_system_context(conversation)
        if system_context:
            messages_payload.append({"role": "system", "content": system_context})

        history_messages = self._recent_history(conversation)
        for msg in history_messages:
            messages_payload.append({"role": msg.role, "content": msg.content})

        messages_payload.append({"role": "user", "content": user_message_content})

        PerplexityMessage.objects.create(
            conversation=conversation,
            role="user",
            content=user_message_content,
        )

        def event_stream():
            assistant_reply = ""
            usage_metadata = None
            external_request_id = None
            try:
                stream = client.chat.completions.create(
                    model="sonar-pro",
                    stream=True,
                    messages=messages_payload,
                )

                for chunk in stream:
                    chunk_text = self._extract_chunk_text(chunk)
                    if chunk_text:
                        assistant_reply += chunk_text
                        yield chunk_text

                    external_request_id = (
                        ProviderUsageCostService.extract_perplexity_request_id(chunk)
                        or external_request_id
                    )
                    chunk_usage = ProviderUsageCostService.extract_perplexity_usage_metadata(chunk)
                    if chunk_usage:
                        usage_metadata = chunk_usage

            except Exception as e:
                print(f"Error in event_stream: {e}")
                yield "Error occurred during streaming."
            else:
                usage_result = None
                if assistant_reply:
                    PerplexityMessage.objects.create(
                        conversation=conversation,
                        role="assistant",
                        content=[{"type": "text", "text": assistant_reply}],
                    )
                    
                    usage_result = UsageTrackingService.record_usage_event(
                        user=request.user,
                        tool=UsageTool.CHAT_ASSISTANT,
                        sub_tool=UsageSubTool.PERPLEXITY,
                        quantity=1,
                        company=getattr(request.user, "company", None),
                        metadata={
                            "conversation_id": str(conversation.conversation_id),
                            "message_length": len(assistant_reply),
                            "files_attached": len(uploaded_files),
                        },
                    )
                    self._update_memory_summary(conversation)

                if usage_metadata:
                    ProviderUsageCostService.record_perplexity_usage_cost(
                        usage_payload=usage_metadata,
                        usage_record=getattr(usage_result, "record", None),
                        external_request_id=external_request_id,
                        metadata={
                            "conversation_id": str(conversation.conversation_id),
                            "files_attached": len(uploaded_files),
                        },
                    )

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response["X-Conversation-ID"] = str(conversation.conversation_id)
        response["Access-Control-Expose-Headers"] = "X-Conversation-ID"
        return response

    def _get_or_create_conversation(self, conversation_id: Optional[str]) -> PerplexityConversation:
        if conversation_id:
            normalized_id = str(conversation_id).strip()
            if not normalized_id:
                return PerplexityConversation.objects.create()
            conversation, _ = PerplexityConversation.objects.get_or_create(
                conversation_id=normalized_id
            )
            return conversation
        return PerplexityConversation.objects.create()

    def _recent_history(self, conversation: PerplexityConversation) -> List[PerplexityMessage]:
        qs = conversation.messages.order_by('-created_at')[: self.max_context_messages]
        history = list(qs)
        history.reverse()
        return history

    def _build_system_context(self, conversation: PerplexityConversation):
        if not conversation.memory_summary:
            return None
        return [
            {
                "type": "text",
                "text": (
                    "Conversation memory summary from prior turns (persisted using the "
                    "Perplexity cookbook approach):\n" + conversation.memory_summary
                )
            }
        ]

    @staticmethod
    def _extract_chunk_text(chunk) -> str:
        choices = getattr(chunk, "choices", None)
        if not choices:
            return ""

        delta = getattr(choices[0], "delta", None)
        if delta is None and isinstance(choices[0], dict):
            delta = choices[0].get("delta")
        if delta is None:
            return ""

        content = getattr(delta, "content", None)
        if content is None and isinstance(delta, dict):
            content = delta.get("content")
        return content or ""

    @staticmethod
    def _extract_text_snippet(content_block):
        if not isinstance(content_block, list):
            return ""
        snippets = []
        for block in content_block:
            if isinstance(block, dict) and block.get("type") == "text":
                snippets.append(block.get("text", ""))
        return " ".join(snippets).strip()

    def _update_memory_summary(self, conversation: PerplexityConversation):
        recent_ids = list(
            conversation.messages.order_by('-created_at').values_list('id', flat=True)[: self.max_context_messages]
        )
        older_messages = (
            conversation.messages.exclude(id__in=recent_ids)
            .filter(included_in_summary=False)
            .order_by('created_at')
        )

        if not older_messages.exists():
            return

        summary_lines = []
        for msg in older_messages:
            text_snippet = self._extract_text_snippet(msg.content)
            if text_snippet:
                summary_lines.append(f"{msg.role.capitalize()}: {text_snippet}")

        if not summary_lines:
            older_messages.update(included_in_summary=True)
            return

        combined_summary = "\n".join(filter(None, [conversation.memory_summary, "\n".join(summary_lines)]))
        conversation.memory_summary = combined_summary[-2000:]
        conversation.save(update_fields=["memory_summary", "updated_at"])
        older_messages.update(included_in_summary=True)
