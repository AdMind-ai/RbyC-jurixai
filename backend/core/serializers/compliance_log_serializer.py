from rest_framework import serializers
from core.models.compliance_log_model import ComplianceLog


class ComplianceLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceLog
        fields = [
            "id",
            "tipo_evento",
            "normativa",
            "autorita",
            "data_rilevazione",
            "versione_precedente",
            "versione_nuova",
            "riassunto_modifica",
            "tag",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ComplianceLogIngestSerializer(serializers.Serializer):
    """
    Serializer per il payload in ingresso da Agente Vera.
    Accetta i campi del JSON concordato e li mappa sul model.
    """
    tipo_evento = serializers.CharField(default="aggiornamento_normativa")
    normativa = serializers.CharField()
    autorita = serializers.CharField(default="", allow_blank=True)
    data_rilevazione = serializers.DateTimeField(required=False, allow_null=True)
    versione_precedente = serializers.JSONField(default=dict)
    versione_nuova = serializers.JSONField(default=dict)
    riassunto_modifica = serializers.CharField(default="", allow_blank=True)
    tag = serializers.CharField(default="LOG")

    def create(self, validated_data):
        return ComplianceLog.objects.create(
            tipo_evento=validated_data.get("tipo_evento", "aggiornamento_normativa"),
            normativa=validated_data["normativa"],
            autorita=validated_data.get("autorita", ""),
            data_rilevazione=validated_data.get("data_rilevazione"),
            versione_precedente=validated_data.get("versione_precedente", {}),
            versione_nuova=validated_data.get("versione_nuova", {}),
            riassunto_modifica=validated_data.get("riassunto_modifica", ""),
            tag=validated_data.get("tag", "LOG"),
            raw_payload=self.initial_data,
        )
