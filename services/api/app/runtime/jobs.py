import logging

# Sync `def` handlers (like runtime/files.py): the B2 calls are blocking boto3,
# so Starlette runs these in its threadpool rather than stalling the event loop.
from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.service import jobs as jobs_service
from app.service import library as library_service
from app.service.jobs import JobNotFoundError
from app.types import (
    CreateJobRequest,
    EnhancementActivityPoint,
    EnhancementJob,
    EnhancementStats,
    LibraryTrack,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# SECURITY: like the file routes, these are intentionally UNAUTHENTICATED and
# bucket-wide (single-tenant demo stance — see docs/SECURITY.md).


def _run_in_background(background_tasks: BackgroundTasks, job_id: str) -> None:
    # FastAPI runs a sync background task in its threadpool, so the blocking
    # AudioSR run happens off the event loop after the response is sent.
    background_tasks.add_task(jobs_service.run_job, job_id)


@router.post("/jobs", response_model=EnhancementJob, status_code=201)
def create_job_endpoint(req: CreateJobRequest, background_tasks: BackgroundTasks):
    try:
        job = jobs_service.create_job(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Storage error creating job") from None
    _run_in_background(background_tasks, job.id)
    return job


@router.get("/jobs", response_model=list[EnhancementJob])
def list_jobs_endpoint():
    return jobs_service.list_all_jobs()


# Static sub-paths declared BEFORE the /{job_id} matcher so they aren't
# swallowed as a job id.
@router.get("/jobs/stats", response_model=EnhancementStats)
def enhancement_stats_endpoint():
    return jobs_service.get_enhancement_stats()


@router.get("/jobs/stats/activity", response_model=list[EnhancementActivityPoint])
def enhancement_activity_endpoint(days: int = 7):
    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 90")
    return jobs_service.get_enhancement_activity(days=days)


@router.get("/jobs/{job_id}", response_model=EnhancementJob)
def get_job_endpoint(job_id: str):
    try:
        return jobs_service.get_job(job_id)
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.post("/jobs/{job_id}/run", response_model=EnhancementJob)
def run_job_endpoint(job_id: str, background_tasks: BackgroundTasks):
    """Re-queue a job (queued/failed/completed) for another enhancement run."""
    try:
        job = jobs_service.get_job(job_id)
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    _run_in_background(background_tasks, job.id)
    return job


@router.delete("/jobs/{job_id}")
def delete_job_endpoint(job_id: str):
    try:
        jobs_service.delete_job(job_id)
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Failed to delete job") from None
    return {"deleted": True, "id": job_id}


@router.get("/library", response_model=list[LibraryTrack])
def library_endpoint():
    return library_service.get_library()
