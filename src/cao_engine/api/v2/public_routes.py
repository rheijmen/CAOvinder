"""Public API v2 routes for B2B customers."""

from fastapi import APIRouter, HTTPException, Depends, Header, Query, Response
from typing import Optional, List
from datetime import datetime
import json
from pathlib import Path

from cao_engine.config import Settings
from cao_engine.api.models.api_key import APIKey


router = APIRouter(prefix="/api/v2", tags=["Public API v2"])


# Dependency injection
def get_settings():
    return Settings()

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
    x_api_key: Optional[str],
    response: Optional[Response] = None,
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
    x_api_key: Optional[str] = Header(None, alias="X-API-Key", description="API Key")
) -> APIKey:
    """Verify API key from header and increment usage counter."""
    return _verify_api_key_internal(x_api_key, response, increment_usage=True)


async def verify_api_key_readonly(
    response: Response,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key", description="API Key")
) -> APIKey:
    """Verify API key from header without incrementing usage counter (for read-only endpoints)."""
    return _verify_api_key_internal(x_api_key, response, increment_usage=False)


@router.get("/cao/search")
async def search_cao(
    company: Optional[str] = Query(None, description="Company name"),
    sector: Optional[str] = Query(None, description="Sector/industry"),
    api_key: APIKey = Depends(verify_api_key)
):
    """Search for applicable CAO by company or sector."""
    settings = get_settings()
    setu_files = list(settings.setu_dir.glob("*.json"))

    results = []
    for setu_file in setu_files:
        with open(setu_file, 'r') as f:
            data = json.load(f)

            # Simple search matching
            if company and company.lower() in setu_file.stem.lower():
                results.append({
                    "id": setu_file.stem,
                    "name": data.get("customer", {}).get("name", "Unknown"),
                    "effective_from": data.get("effectivePeriod", {}).get("validFrom"),
                    "effective_to": data.get("effectivePeriod", {}).get("validTo"),
                    "match_type": "company"
                })
            elif sector and sector.lower() in setu_file.stem.lower():
                results.append({
                    "id": setu_file.stem,
                    "name": data.get("customer", {}).get("name", "Unknown"),
                    "effective_from": data.get("effectivePeriod", {}).get("validFrom"),
                    "effective_to": data.get("effectivePeriod", {}).get("validTo"),
                    "match_type": "sector"
                })

    return {
        "results": results,
        "count": len(results),
        "search": {
            "company": company,
            "sector": sector
        }
    }


@router.get("/cao/{cao_id}/current")
async def get_current_cao(cao_id: str, api_key: APIKey = Depends(verify_api_key)):
    """Get current version of a specific CAO."""
    settings = get_settings()
    cao_file = settings.setu_dir / f"{cao_id}.json"

    if not cao_file.exists():
        raise HTTPException(status_code=404, detail=f"CAO {cao_id} not found")

    with open(cao_file, 'r') as f:
        data = json.load(f)

    return {
        "id": cao_id,
        "documentId": data.get("documentId"),
        "customer": data.get("customer"),
        "effectivePeriod": data.get("effectivePeriod"),
        "version": data.get("versionCode", "1.0"),
        "_metadata": data.get("_extraction_metadata", {})
    }


@router.get("/cao/{cao_id}/salary-scales")
async def get_salary_scales(cao_id: str, api_key: APIKey = Depends(verify_api_key)):
    """Get salary scales (loongebouw) from CAO."""
    settings = get_settings()
    cao_file = settings.setu_dir / f"{cao_id}.json"

    if not cao_file.exists():
        raise HTTPException(status_code=404, detail=f"CAO {cao_id} not found")

    with open(cao_file, 'r') as f:
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

    with open(cao_file, 'r') as f:
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

    with open(cao_file, 'r') as f:
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


@router.get("/changes/feed")
async def get_changes_feed(
    since: Optional[datetime] = Query(None, description="Changes since date"),
    cao_ids: Optional[List[str]] = Query(None, description="Filter by CAO IDs"),
    api_key: APIKey = Depends(verify_api_key)
):
    """Get feed of CAO changes."""

    # This would query a database of changes in production
    changes = [
        {
            "id": "change_001",
            "cao_id": "metalektro-cao",
            "type": "wage_increase",
            "description": "2.5% wage increase effective January 2025",
            "effective_date": "2025-01-01",
            "detected_at": "2024-12-15T10:30:00Z"
        }
    ]

    if cao_ids:
        changes = [c for c in changes if c["cao_id"] in cao_ids]

    if since:
        changes = [c for c in changes
                  if datetime.fromisoformat(c["detected_at"].replace("Z", "+00:00")) > since]

    return {
        "changes": changes,
        "count": len(changes),
        "filters": {
            "since": since.isoformat() if since else None,
            "cao_ids": cao_ids
        }
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