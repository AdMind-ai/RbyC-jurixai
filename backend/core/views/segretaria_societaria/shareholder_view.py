from rest_framework import generics, permissions, status
from rest_framework.response import Response
import logging
from core.models.segreteria_societaria.shareholder_model import Shareholder
from core.serializers.segretaria_societaria.shareholder_serializer import ShareholderSerializer

logger = logging.getLogger(__name__)


class ShareholderListCreateView(generics.ListCreateAPIView):
    queryset = Shareholder.objects.all()
    serializer_class = ShareholderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # Log incoming data to help debug 400s from the frontend
        logger.debug('Shareholder create request data: %s', request.data)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.error('Shareholder serializer errors: %s', serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class ShareholderUpdateView(generics.UpdateAPIView):
    queryset = Shareholder.objects.all()
    serializer_class = ShareholderSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'
