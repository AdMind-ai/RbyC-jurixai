from rest_framework import generics, permissions
from core.models.segreteria_societaria.officer_model import Officer
from core.serializers.segretaria_societaria.officer_serializer import OfficerSerializer

class OfficerListCreateView(generics.ListCreateAPIView):
    queryset = Officer.objects.all()
    serializer_class = OfficerSerializer
    permission_classes = [permissions.IsAuthenticated]

class OfficerUpdateView(generics.UpdateAPIView):
    queryset = Officer.objects.all()
    serializer_class = OfficerSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'
