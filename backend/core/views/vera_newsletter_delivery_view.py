"""
POST /api/vera/newsletter/
Riceve la newsletter generata da Agente Vera e la persiste come SavedNewsletter(source='auto').
Crea anche una Notification di tipo newsletter_auto.
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
    POST /api/vera/newsletter/ — consegna della newsletter generata da Agente Vera.

    Payload atteso:
    {
      "tipo_evento": "newsletter_mensile",
      "periodo": {"inizio": "2026-06-25", "fine": "2026-07-25"},
      "titolo": "Newsletter Compliance — Luglio 2026",
      "contenuto_markdown": "# Titolo\n\n...",
      "quantita_aggiornamenti": 3,
      "generato_il": "2026-07-25T09:00:00Z",
      "stato": "pubblicato"
    }
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        expected_key = getattr(settings, "VERA_API_SERVER_KEY", None) or getattr(settings, "VERA_LOG_API_KEY", None)
        if not expected_key:
            return Response(
                {"detail": "Vera newsletter delivery non configurata."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if request.headers.get("X-Vera-Api-Key") != expected_key:
            logger.warning("VeraNewsletterDeliveryView: richiesta non autorizzata.")
            return Response({"detail": "Invalid Vera API key."}, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data

        titolo = data.get("titolo", "")
        contenuto = data.get("contenuto_markdown", "")
        tipo_evento = data.get("tipo_evento", "newsletter_mensile")
        periodo = data.get("periodo", {})
        quantita_aggiornamenti = data.get("quantita_aggiornamenti")
        generato_il = data.get("generato_il")
        stato = data.get("stato", "pubblicato")

        if not contenuto:
            return Response({"detail": "contenuto_markdown è obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)

        if not titolo:
            inizio = periodo.get("inizio", "")
            fine = periodo.get("fine", "")
            titolo = f"Newsletter Compliance — {fine or inizio or 'Auto'}"

        # Conversione generato_il se presente
        generated_at_dt = None
        if generato_il:
            try:
                from datetime import datetime, timezone as tz
                for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ"):
                    try:
                        generated_at_dt = datetime.strptime(generato_il, fmt).replace(tzinfo=tz.utc)
                        break
                    except ValueError:
                        pass
            except Exception:
                pass

        newsletter = SavedNewsletter.objects.create(
            title=titolo,
            content=contenuto,
            newsletter_type="newsletter",
            source="auto",
            generated_at=generated_at_dt,
        )

        # Notifica
        try:
            body_parts = []
            if periodo.get("inizio") and periodo.get("fine"):
                body_parts.append(f"Periodo: {periodo['inizio']} → {periodo['fine']}.")
            if quantita_aggiornamenti is not None:
                plurale = "aggiornamento" if quantita_aggiornamenti == 1 else "aggiornamenti"
                body_parts.append(f"Basata su {quantita_aggiornamenti} {plurale} normativi.")
            body_parts.append("Disponibile nella sezione Newsletter → Archivio.")

            Notification.objects.create(
                notification_type=NotificationType.NEWSLETTER_AUTO,
                title=f"Nuova newsletter disponibile — {titolo}",
                body=" ".join(body_parts),
                reference_id=str(newsletter.id),
                reference_type="newsletter",
            )
        except Exception as exc:
            logger.warning("Impossibile creare notifica per newsletter Vera: %s", exc)

        logger.info(
            "VeraNewsletterDeliveryView: newsletter '%s' (id=%s) salvata, tipo_evento=%s, stato=%s",
            titolo, newsletter.id, tipo_evento, stato,
        )

        return Response(
            {
                "id": str(newsletter.id),
                "status": "created",
                "titolo": titolo,
                "created_at": newsletter.created_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )
