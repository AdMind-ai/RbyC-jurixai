from rest_framework import serializers
from core.models.vera_usage_model import VeraUsageRecord


class VeraUsageRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = VeraUsageRecord
        fields = [
            "id", "date", "provider", "model",
            "input_tokens", "output_tokens", "total_tokens",
            "request_count", "cost_eur", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class VeraUsageIngestSerializer(serializers.Serializer):
    """
    Payload inviato dal backend di tracciatura (Anthropic / OpenAI hook).
    Supporta upsert: se esiste già un record per (date, provider, model)
    i token e i costi vengono SOMMATI.
    """
    date          = serializers.DateField()
    provider      = serializers.ChoiceField(choices=["openai", "anthropic"])
    model         = serializers.CharField(default="", allow_blank=True)
    input_tokens  = serializers.IntegerField(default=0, min_value=0)
    output_tokens = serializers.IntegerField(default=0, min_value=0)
    total_tokens  = serializers.IntegerField(default=0, min_value=0)
    request_count = serializers.IntegerField(default=1, min_value=0)
    cost_eur      = serializers.DecimalField(
        max_digits=12, decimal_places=6, required=False, allow_null=True
    )

    def create(self, validated_data):
        date          = validated_data["date"]
        provider      = validated_data["provider"]
        model         = validated_data.get("model", "")
        input_tokens  = validated_data.get("input_tokens", 0)
        output_tokens = validated_data.get("output_tokens", 0)
        total_tokens  = validated_data.get("total_tokens", 0) or (input_tokens + output_tokens)
        request_count = validated_data.get("request_count", 1)
        cost_eur      = validated_data.get("cost_eur")

        obj, created = VeraUsageRecord.objects.get_or_create(
            date=date, provider=provider, model=model,
            defaults={
                "input_tokens":  input_tokens,
                "output_tokens": output_tokens,
                "total_tokens":  total_tokens,
                "request_count": request_count,
                "cost_eur":      cost_eur,
                "raw_payload":   self.initial_data,
            }
        )

        if not created:
            # Upsert: somma i valori incrementali
            obj.input_tokens  += input_tokens
            obj.output_tokens += output_tokens
            obj.total_tokens  += total_tokens
            obj.request_count += request_count
            if cost_eur is not None:
                obj.cost_eur = (obj.cost_eur or 0) + cost_eur
            obj.save(update_fields=[
                "input_tokens", "output_tokens", "total_tokens",
                "request_count", "cost_eur", "updated_at",
            ])

        return obj
