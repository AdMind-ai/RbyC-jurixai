from rest_framework import serializers
from core.models.segreteria_societaria.officer_model import Officer

class OfficerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Officer
        fields = ['id', 'company', 'name', 'role', 'appointed_date', 'expiry_date']
