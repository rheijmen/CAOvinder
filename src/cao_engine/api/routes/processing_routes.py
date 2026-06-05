"""
Processing jobs API routes for real-time pipeline monitoring
"""
import asyncio
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()

class ProcessingJob(BaseModel):
    id: str
    cao_name: str
    status: str  # "queued", "running", "complete", "failed"
    stage: str  # "ocr", "gemini", "mistral_review", "judge", "validation"
    progress: int  # 0-100
    started_at: datetime | None = None
    message: str = ""
    error_details: str | None = None
    retry_from_step: int | None = None
    ocr_file: str | None = None

# In-memory storage for active jobs (in production, use Redis or DB)
active_jobs: dict[str, ProcessingJob] = {}

# Removed mock job - using real data now
# metalektro_job = ProcessingJob(...)
# active_jobs[metalektro_job.id] = metalektro_job

@router.post("/api/v1/jobs")
async def create_job(cao_name: str):
    """Create a new processing job"""
    job_id = str(uuid.uuid4())
    job = ProcessingJob(
        id=job_id,
        cao_name=cao_name,
        status="running",
        stage="ocr",
        progress=0,
        started_at=datetime.now(UTC),
        message="Starting OCR processing..."
    )
    active_jobs[job_id] = job
    return job

@router.get("/api/v1/jobs")
async def list_jobs(status: str | None = Query(None)):
    """List all processing jobs"""
    jobs = list(active_jobs.values())
    if status:
        jobs = [j for j in jobs if j.status == status]
    return {"data": jobs, "total": len(jobs)}

@router.get("/api/v1/jobs/{job_id}")
async def get_job(job_id: str):
    """Get a specific job status"""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return active_jobs[job_id]

@router.put("/api/v1/jobs/{job_id}")
async def update_job(job_id: str, stage: str, progress: int, message: str):
    """Update job progress"""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = active_jobs[job_id]
    job.stage = stage
    job.progress = progress
    job.message = message
    if progress >= 100:
        job.status = "complete"
    return job

async def run_retry_in_background(job_id: str, ocr_file: str, step: int, cao_name: str):
    """Run the retry command in the background and update job status"""
    try:
        # Update job status to running
        if job_id in active_jobs:
            job = active_jobs[job_id]
            job.status = "running"
            job.message = f"Retrying from step {step}"
            job.error_details = None
            job.started_at = datetime.now(UTC)

            # Set appropriate stage based on retry step
            if step == 2:
                job.stage = "mistral_review"
                job.progress = 50
            elif step == 3:
                job.stage = "judge"
                job.progress = 75

        # Run the retry command
        cmd = [
            "python", "-m", "cao_engine.cli_retry",
            "retry-from-step", ocr_file,
            "--step", str(step),
            "--cao", cao_name
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/Users/macbookpro/DEV/202602_CAOvinder"
        )

        # Simulate progress updates
        if job_id in active_jobs:
            job = active_jobs[job_id]
            if step == 2:
                await asyncio.sleep(5)
                job.message = "Mistral Large reviewing Gemini output..."
                job.progress = 60

        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            # Success
            if job_id in active_jobs:
                job = active_jobs[job_id]
                job.status = "complete"
                job.progress = 100
                job.message = "Pipeline completed successfully"
                job.stage = "validation"
                job.error_details = None
        else:
            # Failed again
            if job_id in active_jobs:
                job = active_jobs[job_id]
                job.status = "failed"
                job.message = "Retry failed"
                error_msg = stderr.decode() if stderr else "Unknown error"
                # Extract meaningful error from stderr
                if "504 Gateway Timeout" in error_msg or "timing out" in error_msg:
                    job.error_details = "Mistral Large timeout again - API unavailable"
                else:
                    job.error_details = error_msg[:500]  # Limit error message length

    except Exception as e:
        if job_id in active_jobs:
            job = active_jobs[job_id]
            job.status = "failed"
            job.message = "Retry error"
            job.error_details = str(e)

@router.post("/api/v1/jobs/{job_id}/retry")
async def retry_job(job_id: str, background_tasks: BackgroundTasks):
    """Retry a failed job from the failure point"""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = active_jobs[job_id]

    if job.status not in ["failed", "complete"]:  # Allow retry on complete for re-validation
        if job.status == "running":
            raise HTTPException(status_code=400, detail="Job is already running")
        raise HTTPException(status_code=400, detail="Can only retry failed or completed jobs")

    if not job.retry_from_step:
        # Default to step 2 if Gemini succeeded
        if job.progress >= 50:
            job.retry_from_step = 2
        else:
            raise HTTPException(status_code=400, detail="Cannot determine retry step")

    if not job.ocr_file:
        raise HTTPException(status_code=400, detail="OCR file path not available")

    # Start retry in background
    background_tasks.add_task(
        run_retry_in_background,
        job_id,
        job.ocr_file,
        job.retry_from_step,
        job.cao_name
    )

    # Update job status immediately
    job.status = "queued"
    job.message = f"Retry queued from step {job.retry_from_step}"

    return {"message": f"Retry initiated for job {job_id}", "job": job}

@router.delete("/api/v1/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job from tracking"""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    del active_jobs[job_id]
    return {"message": f"Job {job_id} deleted"}