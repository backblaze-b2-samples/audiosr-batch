"""Tests for enhancement-job orchestration.

The AudioSR engine and every B2 call are stubbed, so these run fast and without
the ML stack or a live bucket. An in-memory dict stands in for the B2-backed
job store to mimic the persist/reload round-trip.
"""

import pytest

from app.repo.audiosr_engine import EnhanceResult
from app.service import jobs as jobs_service
from app.types import CreateJobRequest, JobStatus, QualityPreset


@pytest.fixture
def store(monkeypatch):
    """Wire the job-store repo calls to an in-memory dict."""
    data: dict[str, object] = {}

    def save_job(job):
        data[job.id] = job.model_copy(deep=True)

    def load_job(job_id):
        job = data.get(job_id)
        return job.model_copy(deep=True) if job else None

    def list_jobs():
        return [j.model_copy(deep=True) for j in data.values()]

    def delete_manifest(job_id):
        data.pop(job_id, None)

    monkeypatch.setattr(jobs_service, "save_job", save_job)
    monkeypatch.setattr(jobs_service, "load_job", load_job)
    monkeypatch.setattr(jobs_service, "list_jobs", list_jobs)
    monkeypatch.setattr(jobs_service, "delete_manifest", delete_manifest)
    monkeypatch.setattr(jobs_service, "object_exists", lambda key: True)
    return data


def test_create_job_persists_queued_with_preset_params(store):
    job = jobs_service.create_job(
        CreateJobRequest(input_key="originals/podcast/ep01.wav", quality_preset=QualityPreset.high)
    )
    assert job.status == JobStatus.queued
    assert job.collection == "podcast"
    assert job.output_key == "enhanced/podcast/ep01.wav"
    assert job.sidecar_key == "enhanced/podcast/ep01.json"
    assert job.params.ddim_steps == 100  # high preset
    assert store[job.id].status == JobStatus.queued


def test_create_job_rejects_non_originals_key(store):
    with pytest.raises(ValueError, match="originals/"):
        jobs_service.create_job(CreateJobRequest(input_key="somewhere/else.wav"))


def test_run_job_completes_and_writes_artifacts(store, monkeypatch):
    puts: dict[str, bytes] = {}
    monkeypatch.setattr(jobs_service, "get_object_bytes", lambda key: b"x" * 100)
    monkeypatch.setattr(
        jobs_service, "put_object_bytes", lambda key, data, ct: puts.__setitem__(key, data)
    )

    def fake_enhance(in_path, out_path, **kwargs):
        with open(out_path, "wb") as f:
            f.write(b"E" * 900)  # 9x amplification
        return EnhanceResult(
            input_sample_rate=16000,
            output_sample_rate=48000,
            input_duration_sec=3.2,
            model_version="audiosr 0.0.7 (basic)",
            device_used="cpu",
        )

    monkeypatch.setattr(jobs_service, "enhance", fake_enhance)

    created = jobs_service.create_job(
        CreateJobRequest(input_key="originals/default/clip.wav", seed=7)
    )
    job = jobs_service.run_job(created.id)

    assert job.status == JobStatus.completed
    assert job.input_sample_rate == 16000
    assert job.output_sample_rate == 48000
    assert job.input_size_bytes == 100
    assert job.output_size_bytes == 900
    assert job.amplification_ratio == 9.0
    assert job.params.seed == 7
    # Enhanced WAV + JSON sidecar both written to B2.
    assert "enhanced/default/clip.wav" in puts
    assert "enhanced/default/clip.json" in puts


def test_run_job_marks_failed_on_engine_error(store, monkeypatch):
    monkeypatch.setattr(jobs_service, "get_object_bytes", lambda key: b"x" * 10)
    monkeypatch.setattr(jobs_service, "put_object_bytes", lambda key, data, ct: None)

    def boom(in_path, out_path, **kwargs):
        raise RuntimeError("AudioSR exploded")

    monkeypatch.setattr(jobs_service, "enhance", boom)

    created = jobs_service.create_job(
        CreateJobRequest(input_key="originals/default/clip.wav")
    )
    job = jobs_service.run_job(created.id)
    assert job.status == JobStatus.failed
    assert "AudioSR exploded" in (job.error or "")


def test_enhancement_stats_aggregate(store, monkeypatch):
    monkeypatch.setattr(jobs_service, "get_object_bytes", lambda key: b"x" * 100)
    monkeypatch.setattr(jobs_service, "put_object_bytes", lambda key, data, ct: None)

    def fake_enhance(in_path, out_path, **kwargs):
        with open(out_path, "wb") as f:
            f.write(b"E" * 500)
        return EnhanceResult(16000, 48000, 2.0, "audiosr 0.0.7 (basic)", "cpu")

    monkeypatch.setattr(jobs_service, "enhance", fake_enhance)

    created = jobs_service.create_job(
        CreateJobRequest(input_key="originals/default/a.wav")
    )
    jobs_service.run_job(created.id)

    stats = jobs_service.get_enhancement_stats()
    assert stats.files_enhanced == 1
    assert stats.total_original_bytes == 100
    assert stats.total_enhanced_bytes == 500
    assert stats.amplification_ratio == 5.0
    assert stats.avg_input_sample_rate == 16000
    assert stats.jobs_by_status["completed"] == 1
