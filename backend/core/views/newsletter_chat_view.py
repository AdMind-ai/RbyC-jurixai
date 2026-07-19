import logging

from rest_framework import permissions, serializers, status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.services.vera_compliance_service import (
    VeraComplianceConfigurationError,
    VeraComplianceService,
    VeraComplianceServiceError,
    build_vera_session_key,
)

logger = logging.getLogger(__name__)

DRAFT_TYPE_LABEL = {
    "newsletter": "Newsletter normativa",
    "pill": "PILL formativo",
}

DRAFT_TYPE_TAG = {
    "newsletter": "[NEWSLETTER]",
    "pill": "[PILL FORMATIVO]",
}


class NewsletterChatInputSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, allow_blank=False)
    session_id = serializers.CharField(required=False, allow_blank=True, default="")
    draft_type = serializers.ChoiceField(
        choices=["newsletter", "pill"],
        required=False,
        default="newsletter",
    )


def _enrich_prompt(message: str, draft_type: str) -> str:
    """
    Adds channel-specific instructions before sending the user message to Vera.
    """
    type_label = DRAFT_TYPE_LABEL.get(draft_type, "Newsletter normativa")
    return (
        f"[Richiesta: {type_label}]\n"
        "ISTRUZIONE DI FORMATO: quando generi la bozza definitiva del documento, "
        "inseriscila SEMPRE all'interno di un unico blocco <bozza> e </bozza>. "
        "Tutto cio che e conversazionale (domande, chiarimenti, intro, conclusioni) "
        "va FUORI dai tag. "
        "Il blocco <bozza>...</bozza> deve essere l'ultimo elemento isolato della risposta, "
        "senza testo dopo la chiusura di </bozza>. "
        'Esempio: "Ecco la bozza:\\n\\n<bozza>...testo...</bozza>"\n\n'
        f"{message}"
    )


class NewsletterChatView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        serializer = NewsletterChatInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        raw_message = serializer.validated_data["message"].strip()
        session_id = serializer.validated_data.get("session_id") or ""
        draft_type = serializer.validated_data.get("draft_type", "newsletter")

        vera_tag = DRAFT_TYPE_TAG.get(draft_type, "[NEWSLETTER]")
        enriched_message = _enrich_prompt(raw_message, draft_type)

        session_context = {}
        if session_id:
            safe_session_id = session_id.replace("\\", "-").replace("/", "-").strip()
            session_context["matter_id"] = f"newsletter-{safe_session_id}"

        session_key = build_vera_session_key(request.user, session_context)

        try:
            service = VeraComplianceService()
            answer = service.send_message(
                messages=[{"role": "user", "content": enriched_message}],
                session_key=session_key,
                tag=vera_tag,
            )
        except VeraComplianceConfigurationError:
            return Response(
                {"detail": "Vera API is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except VeraComplianceServiceError:
            return Response(
                {"detail": "Error calling Vera compliance service."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {"answer": answer, "sessionKey": session_key},
            status=status.HTTP_200_OK,
        )
