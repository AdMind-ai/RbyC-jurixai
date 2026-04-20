import hashlib
import re

from django.db import models
from django.utils import timezone


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256((raw_key or "").encode("utf-8")).hexdigest()


class IntegrationClient(models.Model):
    customer_code = models.CharField(max_length=128, unique=True)
    client_name = models.CharField(max_length=255)
    bucket_name = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(blank=True, null=True)
    sync_status = models.CharField(max_length=32, default="idle")
    sync_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["active", "customer_code"]),
            models.Index(fields=["bucket_name"]),
        ]

    def __str__(self):
        return f"{self.client_name} ({self.customer_code})"


class IntegrationApiKey(models.Model):
    client = models.ForeignKey(
        IntegrationClient,
        on_delete=models.CASCADE,
        related_name="api_keys",
    )
    key_hash = models.CharField(max_length=64, unique=True)
    active = models.BooleanField(default=True)
    description = models.CharField(max_length=255, blank=True)
    environment = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["active", "key_hash"]),
            models.Index(fields=["client", "active"]),
        ]

    @classmethod
    def hash_key(cls, raw_key: str) -> str:
        return hash_api_key(raw_key)

    def __str__(self):
        return f"{self.client} - {self.description or self.environment or 'API key'}"


class DocumentIndex(models.Model):
    STATUS_PENDING = "pending"
    STATUS_READY = "ready"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_READY, "Ready"),
        (STATUS_FAILED, "Failed"),
        (STATUS_SKIPPED, "Skipped"),
    ]

    client = models.ForeignKey(
        IntegrationClient,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    bucket_name = models.CharField(max_length=255)
    object_key = models.TextField()
    filename = models.CharField(max_length=512)
    extension = models.CharField(max_length=32, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    last_modified = models.DateTimeField(blank=True, null=True)
    etag = models.CharField(max_length=128, blank=True)
    year = models.CharField(max_length=4, blank=True)
    document_type = models.CharField(max_length=64, default="altro")
    text_preview = models.TextField(blank=True)
    extracted_text = models.TextField(blank=True)
    extraction_status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    extraction_error = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    indexed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["client", "object_key"],
                name="unique_document_index_client_object_key",
            )
        ]
        indexes = [
            models.Index(fields=["client", "active", "document_type"]),
            models.Index(fields=["client", "active", "year"]),
            models.Index(fields=["client", "active", "last_modified"]),
            models.Index(fields=["bucket_name"]),
        ]

    def __str__(self):
        return self.object_key

    @staticmethod
    def infer_year(object_key: str) -> str:
        match = re.search(r"(?:^|/)(20\d{2})(?:[./_-]|/|$)", object_key or "")
        return match.group(1) if match else ""

    @staticmethod
    def infer_document_type(object_key: str) -> str:
        value = (object_key or "").lower()
        type_patterns = [
            ("verbale", ["verbale", "verbali"]),
            ("convocazione", ["convocazione", "convocazioni"]),
            ("estratto", ["estratto"]),
            ("regolamento", ["regolamento", "regolamenti"]),
            ("relazione", ["relazione", "relazioni"]),
            ("policy", ["policy", "politica", "policies"]),
            ("procedura", ["procedura", "procedure"]),
            ("materiali", ["materiali", "documenti"]),
            ("email", [".eml"]),
        ]
        for document_type, patterns in type_patterns:
            if any(pattern in value for pattern in patterns):
                return document_type
        return "altro"
