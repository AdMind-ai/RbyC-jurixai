from core.serializers.segretaria_societaria.officer_serializer import OfficerSerializer
from core.serializers.segretaria_societaria.shareholder_serializer import ShareholderSerializer
from rest_framework import serializers
from core.models.segreteria_societaria.company_model import Company
import os


class CompanySerializer(serializers.ModelSerializer):
    officers = OfficerSerializer(many=True, read_only=True)
    shareholders = ShareholderSerializer(many=True, read_only=True)
    letterhead_filename = serializers.SerializerMethodField()

    def get_letterhead_filename(self, obj):
        if not obj.letterhead_file:
            return None
        try:
            return os.path.basename(obj.letterhead_file.name)
        except Exception:
            # Fallback to URL parse
            try:
                return os.path.basename(obj.letterhead_file.url)
            except Exception:
                return None

    class Meta:
        model = Company
        fields = '__all__'

    def validate(self, data):
        # If VAT number is provided, ensure it's unique among other companies
        vat = data.get('vat_number')
        if vat:
            qs = Company.objects.filter(vat_number=vat)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({'vat_number': 'A company with this VAT number already exists.'})
        return data