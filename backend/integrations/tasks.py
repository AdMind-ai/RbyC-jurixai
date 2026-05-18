import logging

from celery import shared_task

from integrations.services.document_index_sync import sync_all_document_indexes
from integrations.services.document_preview import (
    build_document_previews_in_batches,
    build_missing_document_previews,
)


logger = logging.getLogger(__name__)


@shared_task
def sync_all_document_indexes_task(deactivate_missing=True):
    results = sync_all_document_indexes(deactivate_missing=deactivate_missing)
    summary = [
        {
            "client_id": result.client_id,
            "customer_code": result.customer_code,
            "bucket_name": result.bucket_name,
            "created_count": result.created_count,
            "updated_count": result.updated_count,
            "deactivated_count": result.deactivated_count,
            "elapsed_seconds": result.elapsed_seconds,
        }
        for result in results
    ]
    logger.info("[document_index_sync] task_completed results=%s", summary)
    return summary


@shared_task
def build_missing_document_previews_task(
    customer_code="",
    limit=500,
    force=False,
    process_all=False,
    max_batches=0,
):
    if process_all:
        result = build_document_previews_in_batches(
            customer_code=customer_code,
            batch_size=limit,
            force=force,
            max_batches=max(0, max_batches),
        )
    else:
        result = build_missing_document_previews(
            customer_code=customer_code,
            limit=limit,
            force=force,
        )
    summary = {
        "customer_code": customer_code or "<all>",
        "processed_count": result.processed_count,
        "skipped_count": result.skipped_count,
        "failed_count": result.failed_count,
        "batch_count": result.batch_count,
        "attempted_count": len(result.attempted_ids),
    }
    logger.info("[document_preview] task_completed result=%s", summary)
    return summary
