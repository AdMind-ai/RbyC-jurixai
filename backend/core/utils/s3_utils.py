import logging
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
