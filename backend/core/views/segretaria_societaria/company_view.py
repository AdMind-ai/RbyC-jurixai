from rest_framework import generics, permissions
from core.models.segreteria_societaria.company_model import Company
from core.serializers.segretaria_societaria.company_serializer import CompanySerializer

class CompanyListCreateView(generics.ListCreateAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]

class CompanyUpdateView(generics.UpdateAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'
