"""Enhancement-job orchestration.

B2 is the system of record: every job is a JSON manifest in the bucket, the
ingested original and the enhanced rendition + sidecar are objects in the
bucket, and there is no application database.

Single-flight: AudioSR is memory-heavy, so a module-level lock serialises the
actual enhancement runs — one job executes at a time and extra runs queue
behind the lock. In-flight status is therefore per-replica (see RELIABILITY.md);
durable job state lives in B2.
"""

import contextlib
import json
import logging
import os
import random
import tempfile
import uuid
from datetime import UTC, datetime
from threading import Lock

from app.config import settings
from app.repo import (
    delete_file,
    delete_manifest,
    get_object_bytes,
    list_jobs,
    load_job,
    object_exists,
    put_object_bytes,
    save_job,
)
from app.repo.audiosr_engine import enhance
from app.types import (
    CreateJobRequest,
    EnhancementActivityPoint,
    EnhancementJob,
    EnhancementParams,
    EnhancementStats,
    JobStatus,
    QualityPreset,
)
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)

# Serialises real enhancement runs (the model is memory-heavy).
_run_lock = Lock()

# Quality preset → diffusion steps. More steps = higher fidelity, slower run.
_PRESET_DDIM: dict[QualityPreset, int] = {
    QualityPreset.fast: 25,
    QualityPreset.balanced: 50,
    QualityPreset.high: 100,
}
_GUIDANCE_SCALE = 3.5


class JobNotFoundError(Exception):
    def __init__(self, detail: str = "Job not found"):
        self.detail = detail
        super().__init__(detail)


def _now() -> datetime:
    return datetime.now(UTC)


def _derive_targets(input_key: str) -> tuple[str, str, str]:
    """From an originals key, derive (collection, output_key, sidecar_key)."""
    rel = input_key
    if rel.startswith(settings.originals_prefix):
        rel = rel[len(settings.originals_prefix):]
    parts = rel.split("/")
    if len(parts) >= 2:
        collection = parts[0]
        name = "/".join(parts[1:])
    else:
        collection = "default"
        name = rel
    base = name.rsplit(".", 1)[0] if "." in name else name
    output_key = f"{settings.enhanced_prefix}{collection}/{base}.wav"
    sidecar_key = f"{settings.enhanced_prefix}{collection}/{base}.json"
    return collection, output_key, sidecar_key


def create_job(req: CreateJobRequest) -> EnhancementJob:
    """Validate the input, resolve params from the preset, persist a queued job."""
    if not req.input_key.startswith(settings.originals_prefix):
        raise ValueError(
            f"input_key must be an ingested original under '{settings.originals_prefix}'"
        )
    if not object_exists(req.input_key):
        raise ValueError(f"No such original in B2: '{req.input_key}'")

    collection, output_key, sidecar_key = _derive_targets(req.input_key)
    seed = req.seed if req.seed is not None else random.randint(0, 2**31 - 1)
    params = EnhancementParams(
        ddim_steps=_PRESET_DDIM[req.quality_preset],
        guidance_scale=_GUIDANCE_SCALE,
        seed=seed,
        model_name="basic",
    )
    now = _now()
    job = EnhancementJob(
        id=uuid.uuid4().hex,
        input_key=req.input_key,
        output_key=output_key,
        sidecar_key=sidecar_key,
        collection=collection,
        status=JobStatus.queued,
        quality_preset=req.quality_preset,
        params=params,
        created_at=now,
        updated_at=now,
    )
    save_job(job)
    logger.info("Created enhancement job %s for %s", job.id, job.input_key)
    return job


def _write_sidecar(job: EnhancementJob, input_size: int, output_size: int) -> None:
    amp = round(output_size / input_size, 3) if input_size else None
    sidecar = {
        "job_id": job.id,
        "input_key": job.input_key,
        "output_key": job.output_key,
        "collection": job.collection,
        "quality_preset": job.quality_preset.value,
        "input_sample_rate": job.input_sample_rate,
        "output_sample_rate": job.output_sample_rate,
        "input_duration_sec": job.input_duration_sec,
        "model_name": job.params.model_name,
        "model_version": job.model_version,
        "device_used": job.device_used,
        "ddim_steps": job.params.ddim_steps,
        "guidance_scale": job.params.guidance_scale,
        "seed": job.params.seed,
        "input_size_bytes": input_size,
        "output_size_bytes": output_size,
        "amplification_ratio": amp,
        "created_at": job.created_at.isoformat(),
        "completed_at": _now().isoformat(),
    }
    put_object_bytes(
        job.sidecar_key, json.dumps(sidecar, indent=2).encode("utf-8"), "application/json"
    )


def run_job(job_id: str) -> EnhancementJob:
    """Execute the AudioSR pipeline for a job (single-flight). Never raises for
    a processing failure — it records the error on the job and returns it."""
    job = load_job(job_id)
    if job is None:
        raise JobNotFoundError()

    with _run_lock:
        job.status = JobStatus.processing
        job.error = None
        job.updated_at = _now()
        save_job(job)

        in_path = out_path = None
        try:
            data = get_object_bytes(job.input_key)
            input_size = len(data)
            ext = os.path.splitext(job.input_key)[1] or ".wav"
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as f:
                f.write(data)
                in_path = f.name
            out_fd, out_path = tempfile.mkstemp(suffix=".wav")
            os.close(out_fd)

            result = enhance(
                in_path,
                out_path,
                ddim_steps=job.params.ddim_steps,
                guidance_scale=job.params.guidance_scale,
                seed=job.params.seed,
                model_name=job.params.model_name,
            )
            with open(out_path, "rb") as f:
                enhanced_bytes = f.read()
            output_size = len(enhanced_bytes)
            put_object_bytes(job.output_key, enhanced_bytes, "audio/wav")

            job.input_sample_rate = result.input_sample_rate
            job.output_sample_rate = result.output_sample_rate
            job.input_duration_sec = result.input_duration_sec
            job.model_version = result.model_version
            job.device_used = result.device_used
            job.input_size_bytes = input_size
            job.output_size_bytes = output_size
            job.amplification_ratio = (
                round(output_size / input_size, 3) if input_size else None
            )
            _write_sidecar(job, input_size, output_size)
            job.status = JobStatus.completed
            job.updated_at = _now()
            save_job(job)
            logger.info(
                "Job %s completed: %d→%d bytes (%.1fx) on %s",
                job.id, input_size, output_size,
                job.amplification_ratio or 0, job.device_used,
            )
        except Exception as e:
            logger.error("Job %s failed: %s", job.id, e, exc_info=True)
            job.status = JobStatus.failed
            job.error = str(e)[:500]
            job.updated_at = _now()
            save_job(job)
        finally:
            for p in (in_path, out_path):
                if p and os.path.exists(p):
                    with contextlib.suppress(OSError):
                        os.unlink(p)
    return job


def get_job(job_id: str) -> EnhancementJob:
    job = load_job(job_id)
    if job is None:
        raise JobNotFoundError()
    return job


def list_all_jobs() -> list[EnhancementJob]:
    jobs = list_jobs()
    jobs.sort(key=lambda j: j.created_at, reverse=True)
    return jobs


def delete_job(job_id: str) -> None:
    """Delete a job's enhanced WAV + sidecar + manifest — scoped to its own
    keys only, never a bulk/shared wipe."""
    job = load_job(job_id)
    if job is None:
        raise JobNotFoundError()
    # delete_object is idempotent in S3, so a never-produced output is a no-op.
    delete_file(job.output_key)
    delete_file(job.sidecar_key)
    delete_manifest(job_id)
    logger.info("Deleted job %s and its artifacts", job_id)


def get_enhancement_stats() -> EnhancementStats:
    jobs = list_jobs()
    by_status: dict[str, int] = {s.value: 0 for s in JobStatus}
    completed = []
    for j in jobs:
        by_status[j.status.value] = by_status.get(j.status.value, 0) + 1
        if j.status == JobStatus.completed:
            completed.append(j)

    total_in = sum(j.input_size_bytes or 0 for j in completed)
    total_out = sum(j.output_size_bytes or 0 for j in completed)
    amp = round(total_out / total_in, 2) if total_in else 0.0
    in_rates = [j.input_sample_rate for j in completed if j.input_sample_rate]
    out_rates = [j.output_sample_rate for j in completed if j.output_sample_rate]
    return EnhancementStats(
        files_enhanced=len(completed),
        jobs_total=len(jobs),
        total_original_bytes=total_in,
        total_enhanced_bytes=total_out,
        total_original_human=humanize_bytes(total_in),
        total_enhanced_human=humanize_bytes(total_out),
        amplification_ratio=amp,
        avg_input_sample_rate=int(sum(in_rates) / len(in_rates)) if in_rates else 0,
        avg_output_sample_rate=int(sum(out_rates) / len(out_rates)) if out_rates else 0,
        jobs_by_status=by_status,
    )


def get_enhancement_activity(days: int = 7) -> list[EnhancementActivityPoint]:
    """Enhanced-output bytes per day over the last N days (completed jobs)."""
    from collections import defaultdict
    from datetime import timedelta

    today = datetime.now(UTC).date()
    cutoff = today - timedelta(days=days - 1)
    totals: dict[str, int] = defaultdict(int)
    for j in list_jobs():
        if j.status != JobStatus.completed or not j.output_size_bytes:
            continue
        d = j.updated_at.date()
        if d >= cutoff:
            totals[d.isoformat()] += j.output_size_bytes
    return [
        EnhancementActivityPoint(
            date=(cutoff + timedelta(days=i)).isoformat(),
            bytes=totals.get((cutoff + timedelta(days=i)).isoformat(), 0),
        )
        for i in range(days)
    ]
