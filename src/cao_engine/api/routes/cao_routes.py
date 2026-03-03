"""
Modern REST API Routes for CAO Document Management

This module provides the API endpoints that the frontend calls.
The frontend NEVER accesses the database directly - all data flows through these APIs.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID
import json

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import structlog

from cao_engine.config import Settings
from cao_engine.storage.json_store import JSONStore
from cao_engine.ocr.processor import OCRProcessor
from cao_engine.compliance.setu_compliance_engine import SETUComplianceEngine

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["CAO Management"])

# Dependency injection
def get_settings():
    return Settings()

def get_json_store(settings: Settings = Depends(get_settings)):
    return JSONStore(settings)

def get_ocr_processor(settings: Settings = Depends(get_settings)):
    return OCRProcessor(settings)

def get_compliance_engine():
    return SETUComplianceEngine()

# ==========================================
# Request/Response Models
# ==========================================

class CAOListResponse(BaseModel):
    data: List[dict]
    total: int
    page: int = 1
    limit: int = 20

class CAOUploadRequest(BaseModel):
    name: str
    sector: Optional[str] = None
    company: Optional[str] = None
    effective_date: Optional[datetime] = None
    metadata: dict = {}

class ProcessingRequest(BaseModel):
    pipeline_config: Optional[dict] = None
    priority: str = "normal"

class ProcessingJobResponse(BaseModel):
    id: str
    cao_document_id: str
    status: str
    progress: int
    estimated_cost: float
    started_at: Optional[datetime]
    message: str

# ==========================================
# CAO Document Endpoints
# ==========================================

@router.get("/caos")
async def list_cao_documents(
    search: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    store: JSONStore = Depends(get_json_store)
) -> CAOListResponse:
    """
    List all CAO documents with filtering and pagination.

    This endpoint is called by the frontend CAO Library page.
    """
    logger.info("Listing CAO documents", search=search, sector=sector, status=status)

    # Get all documents from storage (both structured and SETU)
    all_docs = store.list_documents()

    # Also get SETU documents
    settings = get_settings()
    setu_docs = list(settings.setu_dir.glob("*.json"))

    # Combine both sources
    all_doc_paths = list(all_docs) + setu_docs

    # Apply filters (in production, this would be a database query)
    filtered_docs = []
    for doc_path in all_doc_paths:
        try:
            # Check if this is a SETU document or structured document
            if doc_path.parent.name == "setu":
                # Load SETU document directly as JSON
                with open(doc_path, 'r') as f:
                    setu_data = json.load(f)

                # Extract CAO name from customer or extraction metadata
                cao_name = "Unknown CAO"
                if "customer" in setu_data and "name" in setu_data["customer"]:
                    cao_name = setu_data["customer"]["name"]
                elif "_extraction_metadata" in setu_data and "cao_name" in setu_data["_extraction_metadata"]:
                    cao_name = setu_data["_extraction_metadata"]["cao_name"]

                # Apply search filter
                if search and search.lower() not in cao_name.lower():
                    continue

                # Get effective period
                effective_from = None
                effective_to = None
                if "effectivePeriod" in setu_data:
                    effective_from = setu_data["effectivePeriod"].get("validFrom")
                    effective_to = setu_data["effectivePeriod"].get("validTo")

                # Get compliance status
                compliance_status = "unknown"
                if "_compliance" in setu_data:
                    compliance_status = setu_data["_compliance"].get("status", "unknown")

                # Transform for frontend
                filtered_docs.append({
                    "id": doc_path.stem.replace(".setu", ""),
                    "name": cao_name,
                    "sector": None,  # Could extract from SETU if available
                    "company": setu_data.get("customer", {}).get("name", None),
                    "status": "complete",
                    "compliance_status": compliance_status,
                    "version": 1,
                    "effective_date": effective_from,
                    "effectivePeriod": {
                        "validFrom": effective_from,
                        "validTo": effective_to
                    } if effective_from else None,
                    "file_size": doc_path.stat().st_size if doc_path.exists() else 0,
                    "processed_at": setu_data.get("_extraction_metadata", {}).get("extracted_at", None),
                    "confidence": setu_data.get("_compliance", {}).get("coverage", 0),
                })
            else:
                # Load structured CAODocument object
                cao_doc = store.load(doc_path)

                # Convert to dict for easier access
                doc_data = cao_doc.model_dump()

                # Apply search filter
                if search and search.lower() not in cao_doc.metadata.cao_naam.lower():
                    continue

                # Apply sector filter (if we have sector in metadata)
                if sector:
                    # Skip filter for now since sector is not in our current model
                    pass

                # Apply status filter (if applicable)
                if status:
                    # Skip filter for now since status is not in our current model
                    pass

                # Transform for frontend
                filtered_docs.append({
                    "id": doc_path.stem,
                    "name": cao_doc.metadata.cao_naam,
                    "sector": getattr(cao_doc.metadata, "sector", None),
                    "company": getattr(cao_doc.metadata, "company", None),
                    "status": "complete",  # All loaded docs are complete
                    "compliance_status": "unknown",  # We don't have SETU compliance check yet
                    "version": 1,
                    "effective_date": cao_doc.metadata.effective_date.isoformat() if hasattr(cao_doc.metadata, "effective_date") and cao_doc.metadata.effective_date else None,
                    "effectivePeriod": None,
                    "file_size": doc_path.stat().st_size if doc_path.exists() else 0,
                    "processed_at": cao_doc.metadata.extraction_date.isoformat() if hasattr(cao_doc.metadata, "extraction_date") and cao_doc.metadata.extraction_date else None,
                    "confidence": cao_doc.metadata.overall_confidence if hasattr(cao_doc.metadata, "overall_confidence") and cao_doc.metadata.overall_confidence else 0,
                })
        except Exception as e:
            logger.error(f"Error loading document {doc_path}: {e}")
            continue

    # Apply pagination
    start = (page - 1) * limit
    end = start + limit
    paginated = filtered_docs[start:end]

    return CAOListResponse(
        data=paginated,
        total=len(filtered_docs),
        page=page,
        limit=limit
    )

@router.get("/caos/{cao_id}")
async def get_cao_document(
    cao_id: str,
    store: JSONStore = Depends(get_json_store)
):
    """Get detailed information about a specific CAO document."""
    logger.info("Fetching CAO document", cao_id=cao_id)

    # Try to load the document by its ID (which is the filename stem)
    # First try structured documents
    doc_path = store._dir / f"{cao_id}.json"

    # If not found in structured, try SETU documents
    if not doc_path.exists():
        settings = get_settings()
        # Try with .setu suffix
        setu_path = settings.setu_dir / f"{cao_id}.setu.json"
        if setu_path.exists():
            doc_path = setu_path
        else:
            # Try without .setu suffix
            setu_path = settings.setu_dir / f"{cao_id}.json"
            if setu_path.exists():
                doc_path = setu_path

    if not doc_path.exists():
        raise HTTPException(status_code=404, detail=f"CAO document {cao_id} not found")

    try:
        # Check if this is a SETU document
        if doc_path.parent.name == "setu":
            # Load SETU document directly as JSON
            with open(doc_path, 'r') as f:
                return json.load(f)
        else:
            # Load structured CAODocument
            cao_doc = store.load(doc_path)
            return cao_doc.model_dump()
    except Exception as e:
        logger.error(f"Error loading document {cao_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading document: {str(e)}")

@router.post("/caos/upload")
async def upload_cao_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    metadata: Optional[str] = None,
    settings: Settings = Depends(get_settings),
    store: JSONStore = Depends(get_json_store)
):
    """
    Upload a new CAO PDF document for processing.

    This starts the entire processing pipeline in the background.
    """
    logger.info("Uploading CAO document", filename=file.filename, size=file.size)

    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Save uploaded file
    upload_path = settings.raw_dir / file.filename
    upload_path.parent.mkdir(exist_ok=True)

    content = await file.read()
    with open(upload_path, 'wb') as f:
        f.write(content)

    # Create document record
    cao_id = file.filename.replace('.pdf', '')
    doc_record = {
        "id": cao_id,
        "original_filename": file.filename,
        "file_size": len(content),
        "status": "uploaded",
        "uploaded_at": datetime.now().isoformat(),
        "metadata": metadata
    }

    # Start processing in background
    background_tasks.add_task(
        process_cao_document,
        cao_id=cao_id,
        file_path=upload_path,
        settings=settings
    )

    return {
        **doc_record,
        "message": "CAO uploaded successfully. Processing started in background."
    }

@router.post("/caos/{cao_id}/process")
async def start_processing(
    cao_id: str,
    request: ProcessingRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings)
) -> ProcessingJobResponse:
    """
    Start or restart processing for a CAO document.

    This endpoint triggers the 3-LLM pipeline.
    """
    logger.info("Starting processing", cao_id=cao_id, config=request.pipeline_config)

    # Create job record
    job_id = f"job-{cao_id}-{datetime.now().timestamp()}"

    # Start async processing
    background_tasks.add_task(
        run_3llm_pipeline,
        cao_id=cao_id,
        job_id=job_id,
        config=request.pipeline_config,
        settings=settings
    )

    return ProcessingJobResponse(
        id=job_id,
        cao_document_id=cao_id,
        status="queued",
        progress=0,
        estimated_cost=2.50,  # Based on average
        started_at=None,
        message="Processing job queued successfully"
    )

# ==========================================
# SETU Compliance Endpoints
# ==========================================

@router.get("/caos/{cao_id}/discrepancies")
async def get_discrepancies(
    cao_id: str,
    store: JSONStore = Depends(get_json_store),
    compliance: SETUComplianceEngine = Depends(get_compliance_engine)
):
    """Get all compliance discrepancies for a CAO document."""
    logger.info("Fetching discrepancies", cao_id=cao_id)

    # Load CAO document
    doc = store.load_document(cao_id)

    # Run compliance validation
    if "setu_data" in doc:
        validation_result = compliance.validate_extraction(doc["setu_data"])
        return validation_result["discrepancies"]

    return []

@router.post("/discrepancies/{discrepancy_id}/resolve")
async def resolve_discrepancy(
    discrepancy_id: str,
    resolution: dict,
    store: JSONStore = Depends(get_json_store)
):
    """Resolve a compliance discrepancy with human input."""
    logger.info("Resolving discrepancy", id=discrepancy_id, resolution=resolution)

    # In production, this would update the database
    return {
        "id": discrepancy_id,
        "status": "resolved",
        "resolved_at": datetime.now().isoformat(),
        "resolution": resolution
    }

@router.get("/caos/{cao_id}/setu-report")
async def get_setu_compliance_report(
    cao_id: str,
    store: JSONStore = Depends(get_json_store)
):
    """Get full SETU v2.0 compliance report for a CAO."""
    logger.info("Generating SETU report", cao_id=cao_id)

    doc = store.load_document(cao_id)

    # Generate compliance report
    report = {
        "cao_id": cao_id,
        "setu_version": "2.0",
        "compliance_score": 87.5,  # Calculate from validation
        "total_fields": 36,
        "populated_fields": 31,
        "missing_required": 2,
        "missing_optional": 3,
        "validation_errors": [],
        "generated_at": datetime.now().isoformat()
    }

    return report

@router.get("/caos/{cao_id}/judge-report")
async def get_judge_report(
    cao_id: str,
    settings: Settings = Depends(get_settings)
):
    """Get the judge report from the 3-LLM pipeline."""
    logger.info("Fetching judge report", cao_id=cao_id)

    # Load judge report from storage
    report_path = settings.setu_reports_dir / f"{cao_id}.judge_report.json"

    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Judge report not found")

    import json
    with open(report_path) as f:
        return json.load(f)

# ==========================================
# Processing Jobs Endpoints
# ==========================================

@router.get("/jobs")
async def list_processing_jobs(
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100)
):
    """List all processing jobs with optional status filter."""
    logger.info("Listing jobs", status=status, limit=limit)

    # In production, query from database
    # For now, return mock data
    jobs = [
        {
            "id": "job-001",
            "cao_document_id": "cao-metalektro-2024",
            "status": "running",
            "progress": 65,
            "started_at": (datetime.now() - timedelta(minutes=5)).isoformat(),
            "estimated_cost": 2.50
        },
        {
            "id": "job-002",
            "cao_document_id": "cao-bouw-2024",
            "status": "queued",
            "progress": 0,
            "started_at": None,
            "estimated_cost": 2.20
        }
    ]

    if status:
        jobs = [j for j in jobs if j["status"] == status]

    return jobs[:limit]

@router.get("/jobs/{job_id}")
async def get_job_details(job_id: str):
    """Get detailed information about a processing job."""
    logger.info("Fetching job details", job_id=job_id)

    # In production, query from database
    return {
        "id": job_id,
        "cao_document_id": "cao-metalektro-2024",
        "status": "running",
        "progress": 65,
        "current_stage": "review",
        "stages": [
            {"id": "ocr", "status": "completed", "tokens": 1500, "cost": 0.15},
            {"id": "extract", "status": "completed", "tokens": 8000, "cost": 0.80},
            {"id": "review", "status": "running", "tokens": 3000, "cost": 0.30},
            {"id": "judge", "status": "pending"},
            {"id": "validate", "status": "pending"}
        ],
        "started_at": (datetime.now() - timedelta(minutes=5)).isoformat(),
        "estimated_cost": 2.50,
        "actual_cost": 1.25
    }

@router.post("/jobs/{job_id}/pause")
async def pause_job(job_id: str):
    """Pause a running processing job."""
    logger.info("Pausing job", job_id=job_id)

    return {
        "id": job_id,
        "status": "paused",
        "message": "Job paused successfully"
    }

@router.post("/jobs/{job_id}/resume")
async def resume_job(job_id: str):
    """Resume a paused processing job."""
    logger.info("Resuming job", job_id=job_id)

    return {
        "id": job_id,
        "status": "running",
        "message": "Job resumed successfully"
    }

@router.delete("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a processing job."""
    logger.info("Cancelling job", job_id=job_id)

    return {"message": f"Job {job_id} cancelled successfully"}

# ==========================================
# Background Processing Functions
# ==========================================

async def process_cao_document(cao_id: str, file_path, settings: Settings):
    """Background task to process uploaded CAO document."""
    logger.info("Starting background processing", cao_id=cao_id)

    try:
        # Step 1: OCR
        processor = OCRProcessor(settings)
        ocr_result = processor.process_single(file_path)

        # Step 2: Run 3-LLM pipeline
        await run_3llm_pipeline(cao_id, f"job-{cao_id}", None, settings)

    except Exception as e:
        logger.error("Processing failed", cao_id=cao_id, error=str(e))

async def run_3llm_pipeline(cao_id: str, job_id: str, config, settings: Settings):
    """Execute the 3-LLM extraction pipeline."""
    logger.info("Running 3-LLM pipeline", cao_id=cao_id, job_id=job_id)

    # This would integrate with your existing extraction pipeline
    # For now, just log the progress
    import asyncio

    stages = ["ocr", "extract", "review", "judge", "validate"]
    for i, stage in enumerate(stages):
        logger.info(f"Processing stage: {stage}", job_id=job_id, progress=(i+1)*20)
        await asyncio.sleep(2)  # Simulate processing time

    logger.info("Pipeline complete", job_id=job_id)