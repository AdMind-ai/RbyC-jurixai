from rest_framework import serializers
from core.models.draft_document.company_document_layout import CompanyDocumentLayout


class CompanyDocumentLayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyDocumentLayout
        fields = [
            'id',
            'name',
            'document_title',
            'letterhead_base64',
            'word_letterhead_base64',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
