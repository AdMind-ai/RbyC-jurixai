import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models.saved_newsletter_model import SavedNewsletter
from core.serializers.newsletter_serializer import (
    SavedNewsletterSerializer,
    SavedNewsletterListSerializer,
    SaveNewsletterSerializer,
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

