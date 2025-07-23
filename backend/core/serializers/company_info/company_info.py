from rest_framework import serializers
from core.models.company_info import CompanyInfo, CompetitorInfo, CEO


class CompetitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompetitorInfo
        fields = ['name', 'stock_symbol', 'sector', 'website']


class CEOSerializer(serializers.ModelSerializer):
    class Meta:
        model = CEO
        fields = ['name', 'role']


class CompanySerializer(serializers.ModelSerializer):
    competitors = CompetitorSerializer(many=True, source='competitors_of')
    ceos = CEOSerializer(many=True)

    class Meta:
        model = CompanyInfo
        fields = [
            'long_name',
            'short_name',
            'stock_symbol',
            'website',
            'description',
            'sector',
            'country',
            'state',
            'city',
            'address',
            'phone',
            'email',
            'competitors',
            'ceos',
        ]
