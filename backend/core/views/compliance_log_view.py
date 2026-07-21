import logging

from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models.compliance_log_model import ComplianceLog
from core.models.notification_model import Notification, NotificationType
from core.serializers.compliance_log_serializer import (
    ComplianceLogIngestSerializer,
    ComplianceLogSerializer,
)

logger = logging.getLogger(__name__)


class ComplianceLogListView(APIView):
    """
    GET  /api/check-compliance/logs/   — elenco log (paginato, ultimi 200)
    POST /api/check-compliance/logs/   — ingestione autenticata pelo app
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = ComplianceLog.objects.all()[:200]
        serializer = ComplianceLogSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ComplianceLogIngestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("ComplianceLog ingest validation error: %s", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        log = serializer.save()
        out = ComplianceLogSerializer(log)
        return Response(out.data, status=status.HTTP_201_CREATED)


def _parse_vera_date(value: str):
    """
    Converte uma string de data no formato YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SSZ
    para um objecto datetime aware (UTC). Lança ValueError se o formato for inválido.
    """
    from django.utils.timezone import make_aware
    from datetime import datetime, timezone as tz

    value = value.strip()
    # Tenta datetime completo primeiro
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=tz.utc)
        except ValueError:
            pass
    # Fallback para data simples: interpreta como início do dia UTC
    try:
        d = datetime.strptime(value, "%Y-%m-%d")
        return d.replace(tzinfo=tz.utc)
    except ValueError:
        raise ValueError(f"Formato de data não reconhecido: {value!r}")


class VeraComplianceLogIngestView(APIView):
    """
    GET  /api/vera/log/?da=YYYY-MM-DD&a=YYYY-MM-DD
         — recupera i log del periodo per Agente Vera.
         Accetta date in formato YYYY-MM-DD o YYYY-MM-DDTHH:MM:SSZ.
    POST /api/vera/log/
         — ingestione machine-to-machine da Agente Vera.
    Autenticazione via header X-Vera-Api-Key.
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def _check_key(self, request):
        expected_key = getattr(settings, "VERA_INBOUND_API_KEY", None)
        if not expected_key:
            return None, Response(
                {"detail": "Vera log ingest is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if request.headers.get("X-Vera-Api-Key") != expected_key:
            logger.warning("VeraComplianceLogIngestView: request não autorizada.")
            return None, Response({"detail": "Invalid Vera API key."}, status=status.HTTP_401_UNAUTHORIZED)
        return expected_key, None

    def get(self, request):
        """
        Recupera i log del periodo specificato tramite ?da=...&a=...
        Accetta YYYY-MM-DD o YYYY-MM-DDTHH:MM:SSZ.
        Se omessi, restituisce tutti i log senza filtro di data.
        """
        _, err = self._check_key(request)
        if err:
            return err

        qs = ComplianceLog.objects.all()

        da_raw = request.query_params.get("da")
        a_raw = request.query_params.get("a")

        if da_raw:
            try:
                da_dt = _parse_vera_date(da_raw)
                qs = qs.filter(data_rilevazione__gte=da_dt)
            except ValueError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if a_raw:
            try:
                from datetime import datetime, timezone as tz
                a_dt = _parse_vera_date(a_raw)
                # Se passato solo come data (senza ora), include l'intera giornata fino alle 23:59:59
                if len(a_raw.strip()) == 10:
                    a_dt = a_dt.replace(hour=23, minute=59, second=59)
                qs = qs.filter(data_rilevazione__lte=a_dt)
            except ValueError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ComplianceLogSerializer(qs, many=True)
        logs = serializer.data
        return Response({"count": len(logs), "logs": logs})

    def post(self, request):
        expected_key = getattr(settings, "VERA_INBOUND_API_KEY", None)
        provided_key = request.headers.get("X-Vera-Api-Key")

        if not expected_key:
            logger.error("VERA_INBOUND_API_KEY non configurata.")
            return Response(
                {"detail": "Vera log ingest is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if provided_key != expected_key:
            logger.warning("Vera log ingest unauthorized request.")
            return Response(
                {"detail": "Invalid Vera API key."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = ComplianceLogIngestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("Vera log ingest validation error: %s", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        log = serializer.save()

        # Crea notifica per tutti gli utenti
        try:
            autorita = log.autorita or "Normativa"
            Notification.objects.create(
                notification_type=NotificationType.COMPLIANCE_LOG,
                title=f"Nuovo aggiornamento normativo — {autorita}",
                body=log.riassunto_modifica or log.normativa[:200],
                reference_id=str(log.id),
                reference_type="compliance_log",
            )
        except Exception as exc:
            logger.warning("Impossibile creare notifica per log compliance: %s", exc)

        return Response(
            {
                "id": str(log.id),
                "status": "created",
                "created_at": log.created_at,
            },
            status=status.HTTP_201_CREATED,
        )


class ComplianceLogDetailView(APIView):
    """
    GET    /api/check-compliance/logs/<uuid>/   — dettaglio singolo log
    DELETE /api/check-compliance/logs/<uuid>/   — elimina (solo admin)
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            log = ComplianceLog.objects.get(pk=pk)
        except ComplianceLog.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ComplianceLogSerializer(log).data)

    def delete(self, request, pk):
        if not request.user.is_staff:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        try:
            log = ComplianceLog.objects.get(pk=pk)
        except ComplianceLog.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        log.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
