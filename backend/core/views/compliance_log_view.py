import logging

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
    POST /api/check-compliance/logs/   — ingestione da Agente Vera
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
