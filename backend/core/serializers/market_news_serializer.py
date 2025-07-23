from rest_framework import serializers


class MarketNewsRequestSerializer(serializers.Serializer):
    type = serializers.ChoiceField(
        choices=[('competitors', 'Competitors'), ('sector', 'Sector')])
    query = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        news_type = attrs.get('type')

        if news_type not in ['competitors', 'sector']:
            raise serializers.ValidationError(
                "Type must be 'competitors' or 'sector'.")

        return attrs
