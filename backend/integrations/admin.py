from django.contrib import admin
from django import forms

from integrations.models import (
    DocumentIndex,
    IntegrationApiKey,
    IntegrationClient,
    IntegrationUsageRecord,
)


class IntegrationApiKeyAdminForm(forms.ModelForm):
    raw_key = forms.CharField(
        required=False,
        label="Raw API key",
        help_text=(
            "Informe a chave em texto puro. O sistema vai gerar o hash "
            "automaticamente ao salvar."
        ),
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )

    class Meta:
        model = IntegrationApiKey
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        raw_key = (cleaned_data.get("raw_key") or "").strip()

        if not self.instance.pk and not raw_key:
            raise forms.ValidationError(
                "Informe uma raw API key para criar o registro."
            )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        raw_key = (self.cleaned_data.get("raw_key") or "").strip()
        if raw_key:
            instance.key_hash = IntegrationApiKey.hash_key(raw_key)
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class IntegrationApiKeyInline(admin.TabularInline):
    model = IntegrationApiKey
    extra = 0
    fields = (
        "description",
        "environment",
        "active",
        "short_key_hash",
        "created_at",
        "updated_at",
    )
    readonly_fields = ("short_key_hash", "created_at", "updated_at")

    @admin.display(description="Key hash")
    def short_key_hash(self, obj):
        if not obj or not obj.key_hash:
            return "-"
        return f"{obj.key_hash[:12]}..."


@admin.register(IntegrationClient)
class IntegrationClientAdmin(admin.ModelAdmin):
    list_display = (
        "client_name",
        "customer_code",
        "bucket_name",
        "active",
        "sync_status",
        "last_sync_at",
        "documents_count",
    )
    list_filter = ("active", "sync_status", "created_at", "updated_at")
    search_fields = ("client_name", "customer_code", "bucket_name")
    readonly_fields = ("created_at", "updated_at", "last_sync_at")
    inlines = [IntegrationApiKeyInline]

    @admin.display(description="Documents")
    def documents_count(self, obj):
        return obj.documents.count()


@admin.register(IntegrationApiKey)
class IntegrationApiKeyAdmin(admin.ModelAdmin):
    form = IntegrationApiKeyAdminForm
    list_display = (
        "client",
        "description",
        "environment",
        "active",
        "short_key_hash",
        "created_at",
    )
    list_filter = ("active", "environment", "created_at", "updated_at")
    search_fields = (
        "client__client_name",
        "client__customer_code",
        "description",
        "environment",
        "key_hash",
    )
    readonly_fields = ("key_hash", "created_at", "updated_at")
    fields = (
        "client",
        "raw_key",
        "key_hash",
        "description",
        "environment",
        "active",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Key hash")
    def short_key_hash(self, obj):
        if not obj.key_hash:
            return "-"
        return f"{obj.key_hash[:12]}..."


@admin.register(DocumentIndex)
class DocumentIndexAdmin(admin.ModelAdmin):
    list_display = (
        "filename",
        "client",
        "document_type",
        "document_family",
        "control_function_tags",
        "topic_tags",
        "year",
        "extension",
        "active",
        "extraction_status",
        "document_date",
        "s3_last_modified",
        "last_modified",
        "indexed_at",
    )
    list_filter = (
        "client",
        "active",
        "document_type",
        "document_family",
        "control_function_tags",
        "topic_tags",
        "year",
        "extension",
        "extraction_status",
        "document_date",
        "s3_last_modified",
        "last_modified",
        "indexed_at",
    )
    search_fields = (
        "filename",
        "object_key",
        "bucket_name",
        "client__client_name",
        "client__customer_code",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "indexed_at",
    )
    date_hierarchy = "s3_last_modified"
    ordering = ("-document_date", "-s3_last_modified", "-indexed_at")


@admin.register(IntegrationUsageRecord)
class IntegrationUsageRecordAdmin(admin.ModelAdmin):
    list_display = (
        "occurred_at",
        "tool",
        "client",
        "api_key",
        "auth_mode",
        "auth_identifier",
        "intent_type",
        "documents_count",
    )
    list_filter = ("tool", "auth_mode", "intent_type", "occurred_at", "client")
    search_fields = (
        "request_id",
        "conversation_id",
        "client__client_name",
        "client__customer_code",
        "auth_identifier",
    )
    readonly_fields = ("created_at",)
