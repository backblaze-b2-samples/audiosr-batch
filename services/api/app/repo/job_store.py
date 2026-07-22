"""B2-backed persistence for enhancement jobs.

Jobs are stored as JSON manifests at ``<jobs_prefix><job_id>.json`` so that B2
is the single system of record — there is no application database. boto3 stays
confined to the repo/ layer; the cached S3 client is reused from `b2_client`.
"""

import logging

from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.repo.b2_client import _invalidate_list_cache, get_s3_client
from app.types import EnhancementJob

logger = logging.getLogger(__name__)


def _manifest_key(job_id: str) -> str:
    return f"{settings.jobs_prefix}{job_id}.json"


def save_job(job: EnhancementJob) -> None:
    """Write (or overwrite) a job manifest to B2. Raises RuntimeError on failure."""
    client = get_s3_client()
    body = job.model_dump_json().encode("utf-8")
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=_manifest_key(job.id),
            Body=body,
            ContentType="application/json",
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"Failed to persist job '{job.id}': {e}") from e
    _invalidate_list_cache()


def load_job(job_id: str) -> EnhancementJob | None:
    """Read a single job manifest from B2, or None if it doesn't exist."""
    client = get_s3_client()
    try:
        response = client.get_object(
            Bucket=settings.b2_bucket_name, Key=_manifest_key(job_id)
        )
        raw = response["Body"].read()
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey", "NotFound"):
            return None
        raise RuntimeError(f"Failed to load job '{job_id}': {e}") from e
    except BotoCoreError as e:
        raise RuntimeError(f"Failed to load job '{job_id}': {e}") from e
    return EnhancementJob.model_validate_json(raw)


def list_jobs() -> list[EnhancementJob]:
    """Read every job manifest under the jobs prefix.

    Fine for a single-tenant demo; a large deployment would page an index
    rather than fan out a GET per manifest. Manifests that fail to parse are
    skipped with a warning rather than failing the whole listing.
    """
    client = get_s3_client()
    jobs: list[EnhancementJob] = []
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "Prefix": settings.jobs_prefix}
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            for obj in response.get("Contents", []):
                key = obj["Key"]
                if not key.endswith(".json"):
                    continue
                try:
                    body = client.get_object(
                        Bucket=settings.b2_bucket_name, Key=key
                    )["Body"].read()
                    jobs.append(EnhancementJob.model_validate_json(body))
                except Exception:
                    logger.warning("Skipping unreadable job manifest: %s", key, exc_info=True)
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"Failed to list jobs: {e}") from e
    return jobs


def delete_manifest(job_id: str) -> None:
    """Delete a job manifest from B2. Raises RuntimeError on failure."""
    client = get_s3_client()
    try:
        client.delete_object(
            Bucket=settings.b2_bucket_name, Key=_manifest_key(job_id)
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"Failed to delete job manifest '{job_id}': {e}") from e
    _invalidate_list_cache()
