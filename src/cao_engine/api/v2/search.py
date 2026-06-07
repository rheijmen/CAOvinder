"""CAO Search API endpoints for v2 — backed by real SETU data (no mock fiction).

Results come from CAOService (canonical SETU documents) joined with the provenance
sidecar at read time. coverage_score is the real inter-model agreement confidence
(0 when no provenance exists yet) — never a fabricated number.
"""
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from cao_engine.api.v2.public_routes import get_cao_service
from cao_engine.serving.cao_service import CAONotFoundError, CAOService

router = APIRouter(prefix="/search", tags=["CAO Search"])

# Module-level dependency marker (avoids B008 function-call-in-defaults)
_SERVICE_DEP = Depends(get_cao_service)


class CAOSearchResult(BaseModel):
    """Single CAO search result."""

    id: str = Field(..., description="Unique CAO identifier")
    name: str = Field(..., description="CAO display name")
    sector: str = Field(..., description="Sector derived from the CAO identifier")
    company: str | None = Field(None, description="Customer/employer name from the SETU document")
    effective_from: str | None = Field(None, description="Start date (ISO 8601)")
    effective_to: str | None = Field(None, description="End date (ISO 8601)")
    coverage_score: int = Field(..., description="Inter-model agreement %, 0 if unknown")
    document_count: int = Field(..., description="Number of canonical SETU documents")
    has_salary_scales: bool = Field(..., description="Whether salary scales are present")
    match_type: str = Field(..., description="How the match was found")
    match_score: float = Field(..., description="Relevance score 0-100")


class CAOSearchResponse(BaseModel):
    """Response for CAO search endpoint."""

    results: list[CAOSearchResult] = Field(..., description="List of matching CAOs")
    total: int = Field(..., description="Total number of results")
    query: dict[str, str | None] = Field(..., description="Search parameters used")
    suggestions: list[str] = Field(default_factory=list, description="Alternative suggestions")


def _sector_from_id(cao_id: str) -> str:
    """Best-effort sector label derived from the CAO id slug (real, not a fixed taxonomy)."""
    slug = re.sub(r"^\d+-", "", cao_id)          # drop leading collector number
    slug = re.split(r"-cao(?:-|\b)", slug)[0]    # text before "-cao..."
    return slug.replace("-", " ").strip().title() or cao_id


def _has_salary_scales(document: dict) -> bool:
    return any(pkg.get("salaryScale") for pkg in (document.get("remuneration") or []))


def _coverage_score(provenance: dict) -> int:
    confidence = provenance.get("confidence")
    return round(confidence * 100) if isinstance(confidence, (int, float)) else 0


def _is_active(effective_to: str | None) -> bool:
    if not effective_to:
        return True
    try:
        date_str = effective_to if "T" in effective_to else f"{effective_to}T00:00:00"
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")) >= datetime.now()
    except ValueError:
        return True


def _build_result(service: CAOService, cao_id: str, match_type: str, match_score: float):
    full = service.get_cao(cao_id)
    document = full["document"]
    customer = document.get("customer") or {}
    period = document.get("effectivePeriod") or {}
    return CAOSearchResult(
        id=cao_id,
        name=customer.get("name") or cao_id,
        sector=_sector_from_id(cao_id),
        company=customer.get("name"),
        effective_from=period.get("validFrom"),
        effective_to=period.get("validTo"),
        coverage_score=_coverage_score(full["provenance"]),
        document_count=1,
        has_salary_scales=_has_salary_scales(document),
        match_type=match_type,
        match_score=match_score,
    )


def _kvk_matches(document: dict, kvk: str) -> bool:
    for legal_id in document.get("customer", {}).get("legalId", []) or []:
        scheme = str(legal_id.get("schemeAgencyId", "")).lower()
        if "kvk" in scheme and str(legal_id.get("value", "")).strip() == kvk.strip():
            return True
    return False


@router.get("/cao", response_model=CAOSearchResponse)
async def search_cao(
    company: str | None = Query(None, description="Company name to search for"),
    sector: str | None = Query(None, description="Industry sector to search in"),
    kvk: str | None = Query(None, description="KVK (Chamber of Commerce) number"),
    active_only: bool = Query(True, description="Only show currently active CAOs"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    service: CAOService = _SERVICE_DEP,
) -> CAOSearchResponse:
    """Search applicable CAOs by company, sector, or KVK number, from real SETU data."""
    if not any([company, sector, kvk]):
        raise HTTPException(
            status_code=400,
            detail="At least one search parameter (company, sector, or kvk) is required",
        )

    scored: dict[str, CAOSearchResult] = {}

    for hit in service.search_caos(company, sector):
        match_type = hit["match_type"]
        match_score = 100.0 if match_type == "company" else 60.0
        scored[hit["id"]] = _build_result(service, hit["id"], match_type, match_score)

    if kvk:
        for cao_id in service.list_cao_ids():
            if cao_id in scored:
                continue
            try:
                document = service.get_cao(cao_id)["document"]
            except CAONotFoundError:
                continue
            if _kvk_matches(document, kvk):
                scored[cao_id] = _build_result(service, cao_id, "kvk", 100.0)

    results = list(scored.values())
    if active_only:
        results = [r for r in results if _is_active(r.effective_to)]
    results.sort(key=lambda r: r.match_score, reverse=True)

    suggestions: list[str] = []
    if not results:
        if company:
            suggestions.append("Try searching by sector instead of company name")
        if sector:
            suggestions.append("Try broader sector terms")
        suggestions.append("Contact support for manual CAO identification")

    return CAOSearchResponse(
        results=results[offset : offset + limit],
        total=len(results),
        query={"company": company, "sector": sector, "kvk": kvk},
        suggestions=suggestions,
    )


@router.get("/sectors", response_model=list[str])
async def list_sectors(
    service: CAOService = _SERVICE_DEP,
) -> list[str]:
    """Distinct sector labels derived from the real CAO set (for autocomplete)."""
    return sorted({_sector_from_id(cao_id) for cao_id in service.list_cao_ids()})


@router.get("/companies", response_model=list[dict[str, str | None]])
async def search_companies(
    q: str = Query(..., min_length=2, description="Search query for company name"),
    service: CAOService = _SERVICE_DEP,
) -> list[dict[str, str | None]]:
    """Companies with a known CAO, derived from real SETU customer data (no fake KVKs)."""
    companies: list[dict[str, str | None]] = []
    for cao_id in service.list_cao_ids():
        try:
            document = service.get_cao(cao_id)["document"]
        except CAONotFoundError:
            continue
        customer = document.get("customer") or {}
        name = customer.get("name")
        if not name or q.lower() not in name.lower():
            continue
        kvk = next(
            (
                str(lid.get("value"))
                for lid in customer.get("legalId", []) or []
                if "kvk" in str(lid.get("schemeAgencyId", "")).lower() and lid.get("value")
            ),
            None,
        )
        companies.append({"name": name, "kvk": kvk, "sector": _sector_from_id(cao_id)})
    return companies
