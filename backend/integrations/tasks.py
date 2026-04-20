import logging

from celery import shared_task

from integrations.services.document_index_sync import sync_all_document_indexes


logger = logging.getLogger(__name__)


@shared_task
def sync_all_document_indexes_task(deactivate_missing=False):
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
