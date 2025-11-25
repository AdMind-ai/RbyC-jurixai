from rest_framework import generics, permissions
from core.models.segreteria_societaria.shareholder_model import Shareholder
from core.serializers.segretaria_societaria.shareholder_serializer import ShareholderSerializer

class ShareholderListCreateView(generics.ListCreateAPIView):
    queryset = Shareholder.objects.all()
    serializer_class = ShareholderSerializer
    permission_classes = [permissions.IsAuthenticated]

class ShareholderUpdateView(generics.UpdateAPIView):
    queryset = Shareholder.objects.all()
    serializer_class = ShareholderSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'
