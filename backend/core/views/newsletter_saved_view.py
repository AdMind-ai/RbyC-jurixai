import logging

from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models.saved_newsletter_model import SavedNewsletter
from core.models.notification_model import Notification, NotificationType
from core.serializers.newsletter_serializer import (
    SavedNewsletterSerializer,
    SavedNewsletterListSerializer,
    SaveNewsletterSerializer,
    VeraNewsletterIngestSerializer,
)

logger = logging.getLogger(__name__)


class SavedNewsletterListCreateView(APIView):
    """
    GET  /api/newsletter/saved/   — lista newsletter salvate (senza content completo)
    POST /api/newsletter/saved/   — salva manualmente una newsletter
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = SavedNewsletter.objects.all()
        serializer = SavedNewsletterListSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = SaveNewsletterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        newsletter = serializer.save()
        out = SavedNewsletterSerializer(newsletter)
        return Response(out.data, status=status.HTTP_201_CREATED)


class SavedNewsletterDetailView(APIView):
    """
    GET    /api/newsletter/saved/<uuid>/  — dettaglio newsletter con content completo
    DELETE /api/newsletter/saved/<uuid>/  — elimina newsletter
    """

    permission_classes = [permissions.IsAuthenticated]

    def _get_object(self, pk):
        try:
            return SavedNewsletter.objects.get(pk=pk)
        except SavedNewsletter.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get_object(pk)
        if not obj:
            return Response({"detail": "Non trovata."}, status=status.HTTP_404_NOT_FOUND)
        serializer = SavedNewsletterSerializer(obj)
        return Response(serializer.data)

    def delete(self, request, pk):
        obj = self._get_object(pk)
        if not obj:
            return Response({"detail": "Non trovata."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VeraNewsletterIngestView(APIView):
    """
    POST /api/newsletter/ingest/
    Endpoint machine-to-machine: Agente Vera invia la newsletter generata automaticamente.
    Autenticazione via header X-Vera-Api-Key.
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        expected_key = getattr(settings, "VERA_API_SERVER_KEY", None)
        provided_key = request.headers.get("X-Vera-Api-Key")

        if not expected_key:
            logger.error("VERA_API_SERVER_KEY non configurata.")
            return Response(
                {"detail": "Newsletter ingest is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if provided_key != expected_key:
            logger.warning("Vera newsletter ingest: unauthorized request.")
            return Response(
                {"detail": "Invalid Vera API key."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = VeraNewsletterIngestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("Vera newsletter ingest validation error: %s", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        newsletter = serializer.save()
        logger.info("Vera newsletter ingested: %s (id=%s)", newsletter.title, newsletter.id)

        # Create notification for all users
        Notification.objects.create(
            notification_type=NotificationType.NEWSLETTER_AUTO,
            title="Newsletter mensile generata da Agente Vera",
            body=f'La newsletter "{newsletter.title}" è stata generata automaticamente ed è disponibile nell\'Archivio Newsletter.',
            reference_id=str(newsletter.id),
            reference_type="saved_newsletter",
        )

        out = SavedNewsletterSerializer(newsletter)
        return Response(out.data, status=status.HTTP_201_CREATED)
