from rest_framework import serializers
from core.utils.get_company_info import get_ceos


class CEONewsSerializer(serializers.Serializer):
    personality = serializers.ChoiceField(choices=[])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ceos = get_ceos()
        ceo_names = [ceo.name for ceo in ceos]
        self.fields['personality'].choices = ceo_names
