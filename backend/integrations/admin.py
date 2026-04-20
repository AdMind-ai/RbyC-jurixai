from django.contrib import admin

from integrations.models import DocumentIndex, IntegrationApiKey, IntegrationClient


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
        "year",
        "extension",
        "active",
        "extraction_status",
        "last_modified",
        "indexed_at",
    )
    list_filter = (
        "client",
        "active",
        "document_type",
        "year",
        "extension",
        "extraction_status",
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
    date_hierarchy = "last_modified"
    ordering = ("-last_modified", "-indexed_at")
