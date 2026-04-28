import logging
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from core.utils.s3_utils import _get_s3_client
from integrations.models import DocumentIndex, IntegrationClient


logger = logging.getLogger(__name__)


@dataclass
class DocumentIndexSyncResult:
    client_id: int
    customer_code: str
    bucket_name: str
    created_count: int = 0
    updated_count: int = 0
    deactivated_count: int = 0
    elapsed_seconds: float = 0.0


def sync_all_document_indexes(deactivate_missing: bool = False):
    s3_client = _get_s3_client()
    results = []
    clients = IntegrationClient.objects.filter(active=True)
    for client in clients:
        results.append(
            sync_client_document_index(
                client=client,
                s3_client=s3_client,
                deactivate_missing=deactivate_missing,
            )
        )
    return results


def sync_client_document_index(
    client: IntegrationClient,
    s3_client=None,
    deactivate_missing: bool = False,
) -> DocumentIndexSyncResult:
    started_at = timezone.now()
    s3_client = s3_client or _get_s3_client()
    logger.info(
        "[document_index_sync] started client=%s bucket=%s",
        client.customer_code,
        client.bucket_name,
    )

    client.sync_status = "syncing"
    client.sync_error = ""
    client.save(update_fields=["sync_status", "sync_error", "updated_at"])

    seen_keys = set()
    created_count = 0
    updated_count = 0
    deactivated_count = 0

    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=client.bucket_name)
        with transaction.atomic():
            for page in pages:
                for obj in page.get("Contents", []):
                    object_key = obj["Key"]
                    seen_keys.add(object_key)
                    defaults = build_document_defaults(client, obj)
                    document, created = DocumentIndex.objects.update_or_create(
                        client=client,
                        object_key=object_key,
                        defaults=defaults,
                    )
                    refresh_enriched_tags(document)
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

            if deactivate_missing:
                deactivated_count = (
                    DocumentIndex.objects.filter(client=client, active=True)
                    .exclude(object_key__in=seen_keys)
                    .update(active=False, updated_at=timezone.now())
                )

        client.last_sync_at = timezone.now()
        client.sync_status = "idle"
        client.sync_error = ""
        client.save(
            update_fields=[
                "last_sync_at",
                "sync_status",
                "sync_error",
                "updated_at",
            ]
        )

        elapsed_seconds = (timezone.now() - started_at).total_seconds()
        logger.info(
            "[document_index_sync] completed client=%s bucket=%s created=%s updated=%s deactivated=%s elapsed=%.2fs",
            client.customer_code,
            client.bucket_name,
            created_count,
            updated_count,
            deactivated_count,
            elapsed_seconds,
        )
        return DocumentIndexSyncResult(
            client_id=client.id,
            customer_code=client.customer_code,
            bucket_name=client.bucket_name,
            created_count=created_count,
            updated_count=updated_count,
            deactivated_count=deactivated_count,
            elapsed_seconds=elapsed_seconds,
        )
    except Exception as exc:
        client.sync_status = "failed"
        client.sync_error = str(exc)
        client.save(update_fields=["sync_status", "sync_error", "updated_at"])
        logger.exception(
            "[document_index_sync] failed client=%s bucket=%s",
            client.customer_code,
            client.bucket_name,
        )
        raise


def build_document_defaults(client: IntegrationClient, obj: dict):
    object_key = obj["Key"]
    filename = object_key.split("/")[-1]
    extension = ""
    if "." in filename:
        extension = "." + filename.rsplit(".", 1)[-1].lower()

    return {
        "bucket_name": client.bucket_name,
        "filename": filename,
        "extension": extension,
        "size_bytes": obj.get("Size") or 0,
        "last_modified": obj.get("LastModified"),
        "etag": (obj.get("ETag") or "").strip('"'),
        "year": DocumentIndex.infer_year(object_key),
        "document_type": DocumentIndex.infer_document_type(object_key),
        "document_family": DocumentIndex.infer_document_family(object_key),
        "control_function_tags": DocumentIndex.infer_control_function_tags(
            object_key
        ),
        "topic_tags": DocumentIndex.infer_topic_tags(object_key),
        "active": True,
        "indexed_at": timezone.now(),
    }


def refresh_enriched_tags(document: DocumentIndex):
    control_function_tags = DocumentIndex.infer_control_function_tags(
        document.object_key,
        document.text_preview,
    )
    topic_tags = DocumentIndex.infer_topic_tags(
        document.object_key,
        document.text_preview,
    )

    update_fields = []
    if document.control_function_tags != control_function_tags:
        document.control_function_tags = control_function_tags
        update_fields.append("control_function_tags")
    if document.topic_tags != topic_tags:
        document.topic_tags = topic_tags
        update_fields.append("topic_tags")

    if update_fields:
        document.save(update_fields=update_fields)
