"""Batch processing data models."""

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class BatchStatus(str, Enum):
    """Batch job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchJobType(str, Enum):
    """Type of batch job."""
    OCR = "ocr"  # Mistral OCR Batch API
    EXTRACTION = "extraction"  # Gemini Batch API
    REVIEW = "review"  # Mistral Large Batch API


class BatchJob(BaseModel):
    """Represents a batch processing job."""

    job_id: str = Field(..., description="Unique batch job ID from API")
    job_type: BatchJobType = Field(..., description="Type of batch job")
    status: BatchStatus = Field(default=BatchStatus.PENDING, description="Current status")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now, description="When job was created")
    started_at: datetime | None = Field(None, description="When job started processing")
    completed_at: datetime | None = Field(None, description="When job completed")

    # Files
    input_file: Path = Field(..., description="Path to input JSONL file")
    output_file: Path | None = Field(None, description="Path to output JSONL file (when completed)")

    # Metadata
    total_items: int = Field(..., description="Total number of items in batch")
    processed_items: int = Field(default=0, description="Number of items processed")
    failed_items: int = Field(default=0, description="Number of items that failed")

    # Cost tracking
    estimated_cost_usd: float = Field(default=0.0, description="Estimated cost in USD")
    actual_cost_usd: float | None = Field(None, description="Actual cost in USD (when completed)")

    # Error tracking
    error_message: str | None = Field(None, description="Error message if job failed")

    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100

    @property
    def is_complete(self) -> bool:
        """Check if job is complete (success or failure)."""
        return self.status in (BatchStatus.COMPLETED, BatchStatus.FAILED, BatchStatus.CANCELLED)

    @property
    def elapsed_seconds(self) -> float | None:
        """Calculate elapsed time in seconds."""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()


class BatchSummary(BaseModel):
    """Summary of all batch jobs in a processing run."""

    ocr_job: BatchJob | None = None
    extraction_job: BatchJob | None = None
    review_job: BatchJob | None = None

    @property
    def total_cost_usd(self) -> float:
        """Calculate total estimated or actual cost."""
        total = 0.0
        for job in [self.ocr_job, self.extraction_job, self.review_job]:
            if job:
                total += job.actual_cost_usd or job.estimated_cost_usd
        return total

    @property
    def all_complete(self) -> bool:
        """Check if all jobs are complete."""
        jobs = [j for j in [self.ocr_job, self.extraction_job, self.review_job] if j]
        return all(j.is_complete for j in jobs)

    @property
    def any_failed(self) -> bool:
        """Check if any job failed."""
        jobs = [j for j in [self.ocr_job, self.extraction_job, self.review_job] if j]
        return any(j.status == BatchStatus.FAILED for j in jobs)
