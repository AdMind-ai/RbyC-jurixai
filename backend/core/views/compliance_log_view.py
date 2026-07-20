import logging

from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models.compliance_log_model import ComplianceLog
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


class VeraComplianceLogIngestView(APIView):
    """
    POST /api/vera/log/ — ingestione machine-to-machine da Agente Vera.
    Autenticazione via header X-Vera-Api-Key.
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        expected_key = getattr(settings, "VERA_LOG_API_KEY", None)
        provided_key = request.headers.get("X-Vera-Api-Key")

        if not expected_key:
            logger.error("VERA_LOG_API_KEY non configurata.")
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
