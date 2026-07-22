from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class JobStatus(StrEnum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class QualityPreset(StrEnum):
    """Finite quality presets. Maps to ddim_steps server-side (see service/jobs.py)."""

    fast = "fast"
    balanced = "balanced"
    high = "high"


class EnhancementParams(BaseModel):
    """Concrete model parameters resolved from a quality preset + seed."""

    ddim_steps: int = 50
    guidance_scale: float = 3.5
    seed: int = 42
    model_name: str = "basic"


class EnhancementJob(BaseModel):
    """One audio super-resolution run. Immutable record — persisted in B2."""

    id: str
    input_key: str
    output_key: str
    sidecar_key: str
    collection: str
    status: JobStatus = JobStatus.queued
    quality_preset: QualityPreset = QualityPreset.balanced
    params: EnhancementParams
    # Populated once the run completes.
    input_sample_rate: int | None = None
    output_sample_rate: int | None = None
    input_duration_sec: float | None = None
    model_version: str | None = None
    device_used: str | None = None
    input_size_bytes: int | None = None
    output_size_bytes: int | None = None
    amplification_ratio: float | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class CreateJobRequest(BaseModel):
    input_key: str
    quality_preset: QualityPreset = QualityPreset.balanced
    # Optional — omit for a random seed (recorded on the job for reproducibility).
    seed: int | None = None


class EnhancementStats(BaseModel):
    files_enhanced: int
    jobs_total: int
    total_original_bytes: int
    total_enhanced_bytes: int
    total_original_human: str
    total_enhanced_human: str
    amplification_ratio: float
    avg_input_sample_rate: int
    avg_output_sample_rate: int
    jobs_by_status: dict[str, int]


class EnhancementActivityPoint(BaseModel):
    date: str
    bytes: int


class LibraryTrack(BaseModel):
    """An ingested original paired with its enhanced rendition (if any)."""

    collection: str
    original_key: str
    original_filename: str
    original_size_bytes: int
    original_size_human: str
    content_type: str
    uploaded_at: datetime
    enhanced_key: str | None = None
    enhanced_size_bytes: int | None = None
    enhanced_size_human: str | None = None
    amplification_ratio: float | None = None
