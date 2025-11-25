from rest_framework import serializers
from core.models.segreteria_societaria.shareholder_model import Shareholder

class ShareholderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shareholder
        fields = ['id', 'company', 'name', 'quota_percentage']