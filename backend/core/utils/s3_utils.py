import logging
from collections import defaultdict
from typing import List, Dict, Optional

from django.conf import settings

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
except Exception:  # pragma: no cover - boto3 may not be installed in some test envs
    boto3 = None
    Config = None
    ClientError = Exception

logger = logging.getLogger(__name__)


def _get_s3_client():
    if boto3 is None:
        raise RuntimeError("boto3 is not installed; please add it to requirements.txt")

    # Allow settings to provide credentials or rely on environment / IAM role
    aws_key = getattr(settings, "AWS_ACCESS_KEY_ID", None)
    aws_secret = getattr(settings, "AWS_SECRET_ACCESS_KEY", None)
    region = getattr(settings, "AWS_S3_REGION_NAME", None)

    kwargs = {
        "config": Config(
            signature_version="s3v4",
            s3={"addressing_style": "virtual"},
        )
    }
    if aws_key and aws_secret:
        kwargs["aws_access_key_id"] = aws_key
        kwargs["aws_secret_access_key"] = aws_secret
    if region:
        kwargs["region_name"] = region
        kwargs["endpoint_url"] = f"https://s3.{region}.amazonaws.com"

    return boto3.client("s3", **kwargs)


def get_presigned_urls(
    keys: List[str],
    bucket: Optional[str] = None,
    expires_in: int = 3600,
) -> Dict[str, str]:
    """
    Given a list of S3 object keys, return a mapping key->presigned GET URL for objects

    - Reads bucket name from `bucket` arg or from settings
      `AWS_STORAGE_BUCKET_NAME`.
    - Returns only keys for which a URL could be generated (missing/permission errors are skipped).
    """
    bucket = (
        bucket
        or getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
    )
    if not bucket:
        logger.error(
            "S3 bucket name not configured "
            "(AWS_STORAGE_BUCKET_NAME)"
        )
        return {}

    try:
        client = _get_s3_client()
    except Exception as e:
        logger.exception("Failed to create S3 client: %s", e)
        return {}

    urls: Dict[str, str] = {}
    for key in keys:
        if not key:
            continue
        try:
            # Validate object exists (optional) - this helps avoid creating URLs for missing objects
            try:
                client.head_object(Bucket=bucket, Key=key)
            except ClientError as he:
                logger.warning("S3 object not found or inaccessible: %s (bucket=%s) - %s", key, bucket, he)
                continue

            url = client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in,
            )
            urls[key] = url
        except Exception as e:
            logger.exception("Failed to generate presigned URL for %s: %s", key, e)
            continue

    return urls


def get_presigned_urls_for_document_keys(
    keys: List[str],
    *,
    customer_code: Optional[str] = None,
    fallback_bucket: Optional[str] = None,
    expires_in: int = 3600,
) -> Dict[str, str]:
    """
    Resolve each document key to its indexed bucket and generate presigned URLs.

    Falls back to a provided bucket only for keys that could not be resolved in
    the index. This keeps links accurate when a response mixes documents that
    belong to different buckets.
    """
    if not keys:
        return {}

    from integrations.models import DocumentIndex

    normalized_keys = []
    seen_keys = set()
    for key in keys:
        if not key:
            continue
        stripped_key = key.strip()
        if not stripped_key or stripped_key in seen_keys:
            continue
        seen_keys.add(stripped_key)
        normalized_keys.append(stripped_key)

    if not normalized_keys:
        return {}

    queryset = DocumentIndex.objects.filter(
        active=True,
        object_key__in=normalized_keys,
        client__active=True,
    ).only("object_key", "bucket_name", "client__customer_code")
    if customer_code:
        queryset = queryset.filter(client__customer_code=customer_code)

    key_to_bucket: Dict[str, str] = {}
    for document in queryset:
        document_key = (document.object_key or "").strip()
        document_bucket = (document.bucket_name or "").strip()
        if not document_key or not document_bucket:
            continue
        key_to_bucket.setdefault(document_key, document_bucket)

    bucket_to_keys: Dict[str, List[str]] = defaultdict(list)
    unresolved_keys: List[str] = []
    for key in normalized_keys:
        resolved_bucket = key_to_bucket.get(key)
        if resolved_bucket:
            bucket_to_keys[resolved_bucket].append(key)
        else:
            unresolved_keys.append(key)

    if fallback_bucket and unresolved_keys:
        bucket_to_keys[fallback_bucket].extend(unresolved_keys)

    urls: Dict[str, str] = {}
    for bucket_name, bucket_keys in bucket_to_keys.items():
        urls.update(
            get_presigned_urls(
                bucket_keys,
                bucket=bucket_name,
                expires_in=expires_in,
            )
        )

    return urls
