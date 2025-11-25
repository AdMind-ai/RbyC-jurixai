from core.serializers.segretaria_societaria.officer_serializer import OfficerSerializer
from core.serializers.segretaria_societaria.shareholder_serializer import ShareholderSerializer
from rest_framework import serializers
from core.models.segreteria_societaria.company_model import Company


class CompanySerializer(serializers.ModelSerializer):
    officers = OfficerSerializer(many=True, read_only=True)
    shareholders = ShareholderSerializer(many=True, read_only=True)

    class Meta:
        model = Company
        fields = '__all__'