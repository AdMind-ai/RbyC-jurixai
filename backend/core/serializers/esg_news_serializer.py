from rest_framework import serializers


class ESGNewsSerializer(serializers.Serializer):
    topic = serializers.ChoiceField(choices=[
        "Evoluzione del contesto normativo",
        "Reati informativi",
        "Responsabilità amministratori",
        "Rischi reputazionali"
    ])
