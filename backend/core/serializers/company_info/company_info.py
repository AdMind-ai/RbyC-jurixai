from rest_framework import serializers
from core.models.company_info import CompanyInfo, CEO


class CEOSerializer(serializers.ModelSerializer):
    class Meta:
        model = CEO
        fields = ['name', 'role']


class CompanySerializer(serializers.ModelSerializer):
    ceos = CEOSerializer(many=True)

    class Meta:
        model = CompanyInfo
        fields = [
            'long_name',
            'short_name',
            'website',
            'description',
            'sector',
            'country',
            'state',
            'city',
            'address',
            'phone',
            'email',
            'ceos',
        ]
