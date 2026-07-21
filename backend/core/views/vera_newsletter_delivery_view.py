"""
POST /api/vera/newsletter/
Recebe a newsletter gerada pelo Agente Vera e persiste como SavedNewsletter(source='auto').
Cria também uma Notification do tipo newsletter_auto.
"""

import logging

from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models.saved_newsletter_model import SavedNewsletter
from core.models.notification_model import Notification, NotificationType

logger = logging.getLogger(__name__)


class VeraNewsletterDeliveryView(APIView):
    """
    POST /api/vera/newsletter/ — entrega da newsletter gerada pelo Agente Vera.

    Payload esperado:
    {
      "tipo_evento": "newsletter_mensal",
      "periodo": {"inicio": "2026-06-25", "fim": "2026-07-25"},
      "titulo": "Newsletter Compliance — Julho 2026",
      "conteudo_markdown": "# Título\n\n...",
      "quantidade_atualizacoes": 3,
      "gerado_em": "2026-07-25T09:00:00Z",
      "status": "publicado"
    }
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def _check_api_key(self, request) -> bool:
        expected_key = getattr(settings, "VERA_API_SERVER_KEY", None) or getattr(settings, "VERA_LOG_API_KEY", None)
        if not expected_key:
            logger.error("Nenhuma VERA_API_SERVER_KEY configurada.")
            return False
        return request.headers.get("X-Vera-Api-Key") == expected_key

    def post(self, request):
        expected_key = getattr(settings, "VERA_API_SERVER_KEY", None) or getattr(settings, "VERA_LOG_API_KEY", None)
        if not expected_key:
            return Response(
                {"detail": "Vera newsletter delivery is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if request.headers.get("X-Vera-Api-Key") != expected_key:
            logger.warning("VeraNewsletterDeliveryView: request não autorizada.")
            return Response({"detail": "Invalid Vera API key."}, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data

        titulo = data.get("titulo", "")
        conteudo = data.get("conteudo_markdown", "")
        tipo_evento = data.get("tipo_evento", "newsletter_mensal")
        periodo = data.get("periodo", {})
        quantidade_atualizacoes = data.get("quantidade_atualizacoes")
        gerado_em = data.get("gerado_em")
        status_vera = data.get("status", "publicado")

        if not conteudo:
            return Response({"detail": "conteudo_markdown é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        if not titulo:
            # Título de fallback a partir do período
            inicio = periodo.get("inicio", "")
            fim = periodo.get("fim", "")
            titulo = f"Newsletter Compliance — {fim or inicio or 'Auto'}"

        # Determina o tipo: "newsletter" é o default para entregas Vera
        newsletter_type = "newsletter"

        # Converte gerado_em se presente
        generated_at_dt = None
        if gerado_em:
            try:
                from datetime import datetime, timezone as tz
                for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ"):
                    try:
                        generated_at_dt = datetime.strptime(gerado_em, fmt).replace(tzinfo=tz.utc)
                        break
                    except ValueError:
                        pass
            except Exception:
                pass

        newsletter = SavedNewsletter.objects.create(
            title=titulo,
            content=conteudo,
            newsletter_type=newsletter_type,
            source="auto",
            generated_at=generated_at_dt,
        )

        # Notifica
        try:
            body_parts = []
            if periodo.get("inicio") and periodo.get("fim"):
                body_parts.append(f"Período: {periodo['inicio']} → {periodo['fim']}.")
            if quantidade_atualizacoes is not None:
                plural = "aggiornamento" if quantidade_atualizacoes == 1 else "aggiornamenti"
                body_parts.append(f"Basata su {quantidade_atualizacoes} {plural} normativi.")
            body_parts.append("Disponibile nella sezione Newsletter → Archivio.")

            Notification.objects.create(
                notification_type=NotificationType.NEWSLETTER_AUTO,
                title=f"Nuova newsletter disponibile — {titulo}",
                body=" ".join(body_parts),
                reference_id=str(newsletter.id),
                reference_type="newsletter",
            )
        except Exception as exc:
            logger.warning("Impossibile creare notifica per newsletter Vera: %s", exc)

        logger.info(
            "VeraNewsletterDeliveryView: newsletter '%s' (id=%s) salvata, tipo_evento=%s, status_vera=%s",
            titulo, newsletter.id, tipo_evento, status_vera,
        )

        return Response(
            {
                "id": str(newsletter.id),
                "status": "created",
                "titulo": titulo,
                "created_at": newsletter.created_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )
