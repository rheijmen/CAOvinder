"""Public API v2 routes for B2B customers."""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response

from cao_engine.api.models.api_key import APIKey
from cao_engine.api.v2.models import (
    CAODetailResponse,
    CAOSearchResponse,
    ErrorResponse,
)
from cao_engine.config import Settings
from cao_engine.serving.cao_service import CAONotFoundError, CAOService

router = APIRouter(
    prefix="/api/v2",
    tags=["CAO Data", "Validation", "Usage"],
)


# Dependency injection
def get_settings():
    return Settings()


def get_cao_service() -> CAOService:
    return CAOService.from_settings(Settings())

# Simple in-memory store for demo (should be PostgreSQL in production)
API_KEYS_STORE = {}


def add_rate_limit_headers(response: Response, api_key: APIKey) -> None:
    """Add rate limit headers to response."""
    remaining = max(0, api_key.monthly_limit - api_key.calls_this_month)

    # Calculate reset timestamp (first day of next month at midnight)
    now = datetime.now()
    if now.month == 12:
        reset_date = datetime(now.year + 1, 1, 1)
    else:
        reset_date = datetime(now.year, now.month + 1, 1)
    reset_timestamp = int(reset_date.timestamp())

    response.headers["X-RateLimit-Limit"] = str(api_key.monthly_limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_timestamp)


def _verify_api_key_internal(
    x_api_key: str | None,
    response: Response | None = None,
    increment_usage: bool = True
) -> APIKey:
    """Internal API key verification logic.

    Args:
        x_api_key: API key from X-API-Key header
        increment_usage: Whether to increment the usage counter (default: True)
    """
    # Check if API key is missing or empty
    if not x_api_key or not x_api_key.strip():
        raise HTTPException(status_code=401, detail="Missing or invalid API key")

    # For demo, create a test key if none exists
    if not API_KEYS_STORE:
        test_key, raw = APIKey.create_new("demo_customer", "Demo Key", 10000)
        API_KEYS_STORE[raw] = test_key
        print(f"📌 Demo API Key created: {raw}")

    # Check if API key exists in store
    if x_api_key not in API_KEYS_STORE:
        raise HTTPException(status_code=401, detail="Invalid API key")

    api_key = API_KEYS_STORE[x_api_key]

    # Check if API key is active (before checking limits)
    if not api_key.is_active:
        raise HTTPException(status_code=401, detail="API key is inactive or disabled")

    # Check if API key has exceeded limits
    if not api_key.can_make_request():
        # Calculate seconds until reset
        now = datetime.now()
        if now.month == 12:
            reset_date = datetime(now.year + 1, 1, 1)
        else:
            reset_date = datetime(now.year, now.month + 1, 1)
        retry_after = int((reset_date - now).total_seconds())

        # Create 429 response with Retry-After header
        raise HTTPException(
            status_code=429,
            detail="Monthly rate limit exceeded",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(api_key.monthly_limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(reset_date.timestamp()))
            }
        )

    # Increment usage counter and update last_used timestamp (if requested)
    if increment_usage:
        api_key.calls_this_month += 1

    api_key.last_used = datetime.now()

    # Add rate limit headers to response if provided
    if response:
        add_rate_limit_headers(response, api_key)

    return api_key


async def verify_api_key(
    response: Response,
    x_api_key: str | None = Header(None, alias="X-API-Key", description="API Key")
) -> APIKey:
    """Verify API key from header and increment usage counter."""
    return _verify_api_key_internal(x_api_key, response, increment_usage=True)


async def verify_api_key_readonly(
    response: Response,
    x_api_key: str | None = Header(None, alias="X-API-Key", description="API Key")
) -> APIKey:
    """Verify API key from header without incrementing usage counter (for read-only endpoints)."""
    return _verify_api_key_internal(x_api_key, response, increment_usage=False)


@router.get(
    "/cao/search",
    response_model=CAOSearchResponse,
    summary="Search for CAO by company or sector",
    description="Find applicable Collective Labour Agreements (CAOs) by searching company names or industry sectors.",
    responses={
        200: {
            "description": "Successful search response with matching CAOs",
            "content": {
                "application/json": {
                    "example": {
                        "results": [
                            {
                                "id": "metalektro-cao",
                                "name": "CAO Metalektro 2024-2025",
                                "effective_from": "2024-06-01",
                                "effective_to": "2025-12-31",
                                "match_type": "sector"
                            }
                        ],
                        "count": 1,
                        "search": {"company": None, "sector": "metalektro"}
                    }
                }
            }
        },
        401: {"model": ErrorResponse, "description": "Invalid API key or unauthorized access"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded - too many requests this month"},
    },
    tags=["CAO Data"]
)
async def search_cao(
    company: str | None = Query(None, description="Filter by company name (case-insensitive partial match)", examples=["Philips"]),
    sector: str | None = Query(None, description="Filter by sector/industry (case-insensitive partial match)", examples=["metalektro"]),
    api_key: APIKey = Depends(verify_api_key),
    service: CAOService = Depends(get_cao_service),
):
    """
    Search for applicable CAO by company or sector.

    Returns a list of CAO documents that match the search criteria.
    """
    results = service.search_caos(company=company, sector=sector)
    return {"results": results, "count": len(results), "search": {"company": company, "sector": sector}}


@router.get(
    "/cao/{cao_id}/current",
    response_model=CAODetailResponse,
    summary="Get current CAO details",
    description="Retrieve the current version and metadata of a specific CAO document.",
    responses={
        200: {"description": "CAO details retrieved successfully"},
        401: {"model": ErrorResponse, "description": "Invalid API key or unauthorized access"},
        404: {"model": ErrorResponse, "description": "CAO not found with the specified ID"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded - too many requests this month"},
    },
    tags=["CAO Data"]
)
async def get_current_cao(
    cao_id: str,
    api_key: APIKey = Depends(verify_api_key),
    service: CAOService = Depends(get_cao_service),
):
    """
    Get current version of a specific CAO.

    Returns the CAO's identity, effective period, customer info, and version.
    """
    try:
        doc = service.get_cao(cao_id)["document"]
    except CAONotFoundError:
        raise HTTPException(status_code=404, detail=f"CAO {cao_id} not found") from None
    return {
        "id": cao_id,
        "documentId": doc.get("documentId"),
        "customer": doc.get("customer"),
        "effectivePeriod": doc.get("effectivePeriod"),
        "version": str(doc.get("versionId", "1")),
        "metadata": {},
    }


@router.get(
    "/cao/{cao_id}",
    summary="Get the full CAO document",
    description=(
        "Returns the complete canonical SETU document for a CAO in one operation, plus provenance."
    ),
    tags=["CAO Data"],
)
async def get_full_cao(
    cao_id: str,
    api_key: APIKey = Depends(verify_api_key),
    service: CAOService = Depends(get_cao_service),
):
    try:
        return service.get_cao(cao_id)
    except CAONotFoundError:
        raise HTTPException(status_code=404, detail=f"CAO {cao_id} not found") from None


@router.get(
    "/cao/{cao_id}/changes",
    summary="Upcoming changes for a CAO (vooruitblik)",
    description="Forward-looking calendar of upcoming CAO changes, sourced from the Momenten store.",
    tags=["CAO Data"],
)
async def get_cao_changes(
    cao_id: str,
    horizon_days: int = Query(90, ge=1, le=730, description="Look-ahead window in days"),
    api_key: APIKey = Depends(verify_api_key),
    service: CAOService = Depends(get_cao_service),
):
    try:
        changes = service.get_upcoming_changes(cao_id, horizon_days=horizon_days)
    except CAONotFoundError:
        raise HTTPException(status_code=404, detail=f"CAO {cao_id} not found") from None
    return {"changes": changes, "count": len(changes), "filters": {"horizon_days": horizon_days}}


@router.get("/cao/{cao_id}/salary-scales")
async def get_salary_scales(cao_id: str, api_key: APIKey = Depends(verify_api_key)):
    """Get salary scales (loongebouw) from CAO."""
    settings = get_settings()
    cao_file = settings.setu_dir / f"{cao_id}.json"

    if not cao_file.exists():
        raise HTTPException(status_code=404, detail=f"CAO {cao_id} not found")

    with open(cao_file) as f:
        data = json.load(f)

    remuneration = data.get("remuneration", {})

    return {
        "cao_id": cao_id,
        "salary_scales": remuneration.get("salaryScales", []),
        "wage_components": remuneration.get("wageComponents", []),
        "minimum_wage": remuneration.get("minimumWage"),
        "effective_date": data.get("effectivePeriod", {}).get("validFrom")
    }


@router.get("/cao/{cao_id}/allowances")
async def get_allowances(cao_id: str, api_key: APIKey = Depends(verify_api_key)):
    """Get allowances (toeslagen) from CAO."""
    settings = get_settings()
    cao_file = settings.setu_dir / f"{cao_id}.json"

    if not cao_file.exists():
        raise HTTPException(status_code=404, detail=f"CAO {cao_id} not found")

    with open(cao_file) as f:
        data = json.load(f)

    allowances = data.get("allowances", [])

    return {
        "cao_id": cao_id,
        "allowances": allowances,
        "count": len(allowances),
        "types": list(set(a.get("type") for a in allowances if a.get("type")))
    }


@router.post("/validate/payroll")
async def validate_payroll(
    payroll_data: dict,
    api_key: APIKey = Depends(verify_api_key)
):
    """Validate payroll data against applicable CAO."""

    # Extract validation inputs
    cao_id = payroll_data.get("cao_id")
    gross_salary = payroll_data.get("gross_salary")
    job_level = payroll_data.get("job_level")
    allowances = payroll_data.get("allowances", {})

    if not cao_id:
        raise HTTPException(status_code=400, detail="cao_id is required")

    settings = get_settings()
    cao_file = settings.setu_dir / f"{cao_id}.json"

    if not cao_file.exists():
        raise HTTPException(status_code=404, detail=f"CAO {cao_id} not found")

    with open(cao_file) as f:
        cao_data = json.load(f)

    # Simple validation logic
    issues = []

    # Check minimum wage
    min_wage = cao_data.get("remuneration", {}).get("minimumWage")
    if min_wage and gross_salary < min_wage:
        issues.append({
            "type": "minimum_wage_violation",
            "severity": "critical",
            "message": f"Salary €{gross_salary} below minimum €{min_wage}",
            "field": "gross_salary"
        })

    # More validation logic would go here...

    return {
        "cao_id": cao_id,
        "validation_date": datetime.now().isoformat(),
        "compliant": len(issues) == 0,
        "issues": issues,
        "coverage_score": 80 if len(issues) == 0 else 40  # Simplified
    }



@router.get("/usage")
async def get_api_usage(api_key: APIKey = Depends(verify_api_key)):
    """Get current API usage statistics."""
    # Calculate remaining BEFORE the increment (which already happened in verify_api_key)
    # So we need to subtract 1 from calls_this_month to get the value before increment
    calls_before_increment = api_key.calls_this_month - 1
    remaining = api_key.monthly_limit - calls_before_increment

    return {
        "customer_id": api_key.customer_id,
        "key_name": api_key.name,
        "calls_this_month": api_key.calls_this_month,
        "monthly_limit": api_key.monthly_limit,
        "remaining": remaining,
        "last_used": api_key.last_used.isoformat() if api_key.last_used else None
    }