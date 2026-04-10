import logging

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from core.utils.s3_utils import _get_s3_client


logger = logging.getLogger(__name__)


def upload_bytes_to_storage(file_data: bytes, object_key: str) -> tuple[str, str]:
    """
    Save raw bytes using Django's configured default storage backend.

    Returns a tuple containing the stored object key and its accessible URL.
    """
    if default_storage.exists(object_key):
        default_storage.delete(object_key)

    saved_key = default_storage.save(object_key, ContentFile(file_data))
    file_url = default_storage.url(saved_key)
    return saved_key, file_url


def get_storage_url(object_key: str) -> str:
    """
    Return a storage-backed URL for an existing object key.
    """
    return default_storage.url(object_key)


def upload_bytes_to_s3_bucket(
    file_data: bytes,
    object_key: str,
    bucket_name: str,
    expires_in: int = 3600,
    content_type: str = "application/octet-stream",
) -> tuple[str, str]:
    """
    Upload raw bytes to a specific S3 bucket and return a presigned download URL.
    """
    if not bucket_name:
        raise ValueError("bucket_name is required")

    client = _get_s3_client()
    client.put_object(
        Bucket=bucket_name,
        Key=object_key,
        Body=file_data,
        ContentType=content_type,
    )
    file_url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name, "Key": object_key},
        ExpiresIn=expires_in,
    )
    return object_key, file_url
