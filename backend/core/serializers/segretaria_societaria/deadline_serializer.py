from rest_framework import serializers
from core.models.segreteria_societaria.deadline import Deadline

class DeadlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deadline
        fields = ['id', 'company', 'title', 'due_date', 'completed', 'category', 'created_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Se for PATCH, torna campos obrigatórios opcionais
        request = self.context.get('request', None)
        if request and (request.method == 'PATCH' or request.method == 'PUT'):
            for field in ['company', 'title', 'due_date', 'category']:
                if field in self.fields:
                    self.fields[field].required = False

    def validate(self, attrs):
        request = self.context.get('request', None)
        if request and (request.method == 'PATCH' or request.method == 'PUT'):
            # Não exige campos obrigatórios em PATCH ou PUT
            return attrs
        # Validação padrão para POST
        for field in ['company', 'title', 'due_date', 'category']:
            if field not in attrs or attrs[field] in [None, '']:
                raise serializers.ValidationError({field: 'This field is required.'})
        return attrs
