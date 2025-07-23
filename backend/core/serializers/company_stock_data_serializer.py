from rest_framework import serializers
from core.models.company_stock_data_model import CompanyStockData


class CompanyStockDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyStockData
        fields = [
            'date',
            'company',
            'stock_symbol',
            'stock_exchange',
            'stock_price_today_usd',
            'stock_price_today_eur',
            'market_cap_usd',
            'market_cap_eur',
            'pe_ratio',
            'sector',
            'stock_volatility_level',
            'short_term_forecast',
            'possible_risk_factors',
            'latest_news',
            'analyst_recommendation',
        ]
