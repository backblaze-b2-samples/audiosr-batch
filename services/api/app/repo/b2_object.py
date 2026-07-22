"""On-demand object body reads and writes.

Kept in its own module because `b2_client.py` is at the 300-line ceiling
enforced by `tests/test_structure.py`. boto3/botocore stays confined to the
repo/ layer; the cached S3 client is reused from `b2_client` for connection
pooling.
"""

import io

from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.repo.b2_client import _invalidate_list_cache, get_s3_client


def get_object_bytes(key: str) -> bytes:
    """Download an object's full body into memory.

    Buffers the whole object, so callers MUST size-guard before calling (see
    `service.files.get_file_detail`). Raises RuntimeError on any S3 failure,
    including a not-found object — callers that need to distinguish "missing"
    should `head` first via `get_file_metadata`.

    The streaming `.read()` stays inside the try: on a large object it can fail
    mid-stream with a BotoCoreError (e.g. ReadTimeoutError, ResponseStreamingError)
    that is not a ClientError, and letting it escape would break the
    RuntimeError contract the caller's 502 mapping relies on.
    """
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
        return response["Body"].read()
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 get_object failed for '{key}': {e}") from e


def put_object_bytes(key: str, data: bytes, content_type: str) -> None:
    """Upload raw bytes to B2 under `key`. Raises RuntimeError on failure.

    Used by the enhancement pipeline to write enhanced WAV renditions, JSON
    sidecars, and job manifests. Invalidates the listing cache so new objects
    show up in listings/stats immediately.
    """
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=io.BytesIO(data),
            ContentType=content_type,
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 put_object failed for '{key}': {e}") from e
    _invalidate_list_cache()


def object_exists(key: str) -> bool:
    """Return True if an object exists at `key`.

    Raises RuntimeError on non-404 S3 failures so callers don't silently treat
    an outage as "missing".
    """
    client = get_s3_client()
    try:
        client.head_object(Bucket=settings.b2_bucket_name, Key=key)
        return True
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey", "NotFound"):
            return False
        raise RuntimeError(f"B2 head_object failed for '{key}': {e}") from e
    except BotoCoreError as e:
        raise RuntimeError(f"B2 head_object failed for '{key}': {e}") from e
