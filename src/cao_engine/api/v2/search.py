"""CAO Search API endpoints for v2."""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/search", tags=["CAO Search"])


class CAOSearchResult(BaseModel):
    """Single CAO search result."""

    id: str = Field(..., description="Unique CAO identifier")
    name: str = Field(..., description="CAO display name")
    sector: str = Field(..., description="Industry sector")
    company: str | None = Field(None, description="Specific company if applicable")
    effective_from: str | None = Field(None, description="Start date (ISO 8601)")
    effective_to: str | None = Field(None, description="End date (ISO 8601)")
    coverage_score: int = Field(..., description="SETU compliance coverage %")
    document_count: int = Field(..., description="Number of processed documents")
    has_salary_scales: bool = Field(..., description="Whether salary scales are available")
    match_type: str = Field(..., description="How the match was found")
    match_score: float = Field(..., description="Relevance score 0-100")


class CAOSearchResponse(BaseModel):
    """Response for CAO search endpoint."""

    results: list[CAOSearchResult] = Field(..., description="List of matching CAOs")
    total: int = Field(..., description="Total number of results")
    query: dict[str, str | None] = Field(..., description="Search parameters used")
    suggestions: list[str] = Field(default_factory=list, description="Alternative search suggestions")


@router.get("/cao", response_model=CAOSearchResponse)
async def search_cao(
    company: str | None = Query(None, description="Company name to search for"),
    sector: str | None = Query(None, description="Industry sector to search in"),
    kvk: str | None = Query(None, description="KVK (Chamber of Commerce) number"),
    active_only: bool = Query(True, description="Only show currently active CAOs"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
) -> CAOSearchResponse:
    """
    Search for applicable CAOs by company, sector, or KVK number.

    This endpoint helps inleners (hiring companies) and staffing agencies find
    the correct CAO that applies to their situation for compliance with
    gelijkwaardige beloning (equivalent remuneration) requirements.
    """

    if not any([company, sector, kvk]):
        raise HTTPException(
            status_code=400,
            detail="At least one search parameter (company, sector, or kvk) is required"
        )

    # Load available CAO data
    data_dir = Path("data/setu")
    results = []

    # Mock data for demonstration - in production, this would query a database
    mock_caos = [
        {
            "id": "metalektro-cao-2024",
            "name": "CAO Metalektro 2024-2027",
            "sector": "Metalektro",
            "company": None,
            "effective_from": "2024-06-01",
            "effective_to": "2027-05-31",
            "coverage_score": 87,
            "document_count": 3,
            "has_salary_scales": True
        },
        {
            "id": "achmea-cao-2023",
            "name": "Achmea CAO 2023-2026",
            "sector": "Verzekeringen",
            "company": "Achmea",
            "effective_from": "2023-12-01",
            "effective_to": "2026-11-30",
            "coverage_score": 92,
            "document_count": 2,
            "has_salary_scales": True
        },
        {
            "id": "ikea-cao-2025",
            "name": "IKEA CAO 2025-2027",
            "sector": "Detailhandel",
            "company": "IKEA",
            "effective_from": "2025-01-01",
            "effective_to": "2027-12-31",
            "coverage_score": 85,
            "document_count": 1,
            "has_salary_scales": True
        },
        {
            "id": "ns-cao-2024",
            "name": "Nederlandse Spoorwegen CAO 2024-2027",
            "sector": "Transport",
            "company": "Nederlandse Spoorwegen",
            "effective_from": "2024-01-01",
            "effective_to": "2027-02-28",
            "coverage_score": 78,
            "document_count": 2,
            "has_salary_scales": True
        },
        {
            "id": "groothandel-bloemen-cao-2024",
            "name": "Groothandel Bloemen & Planten CAO 2024-2027",
            "sector": "Groothandel",
            "company": None,
            "effective_from": "2024-01-01",
            "effective_to": "2027-12-31",
            "coverage_score": 73,
            "document_count": 1,
            "has_salary_scales": True
        },
        {
            "id": "nam-cao-2025",
            "name": "NAM (Nederlandse Aardolie Maatschappij) CAO 2025-2027",
            "sector": "Energie",
            "company": "NAM",
            "effective_from": "2025-01-01",
            "effective_to": "2027-12-31",
            "coverage_score": 88,
            "document_count": 2,
            "has_salary_scales": True
        },
        {
            "id": "shell-cao-2024",
            "name": "Shell Nederland CAO 2024-2026",
            "sector": "Energie",
            "company": "Shell Nederland",
            "effective_from": "2024-04-01",
            "effective_to": "2026-03-31",
            "coverage_score": 91,
            "document_count": 3,
            "has_salary_scales": True
        },
        {
            "id": "albert-heijn-cao-2024",
            "name": "Albert Heijn CAO 2024-2026",
            "sector": "Detailhandel",
            "company": "Albert Heijn",
            "effective_from": "2024-07-01",
            "effective_to": "2026-06-30",
            "coverage_score": 82,
            "document_count": 2,
            "has_salary_scales": True
        },
        {
            "id": "ing-cao-2025",
            "name": "ING Bank CAO 2025-2027",
            "sector": "Financiële dienstverlening",
            "company": "ING Bank",
            "effective_from": "2025-01-01",
            "effective_to": "2027-12-31",
            "coverage_score": 89,
            "document_count": 2,
            "has_salary_scales": True
        },
        {
            "id": "rabobank-cao-2024",
            "name": "Rabobank CAO 2024-2026",
            "sector": "Financiële dienstverlening",
            "company": "Rabobank",
            "effective_from": "2024-07-01",
            "effective_to": "2026-06-30",
            "coverage_score": 86,
            "document_count": 2,
            "has_salary_scales": True
        },
        {
            "id": "horeca-cao-2024",
            "name": "Horeca CAO 2024-2026",
            "sector": "Horeca",
            "company": None,
            "effective_from": "2024-04-01",
            "effective_to": "2026-03-31",
            "coverage_score": 75,
            "document_count": 2,
            "has_salary_scales": True
        },
        {
            "id": "bouw-cao-2024",
            "name": "Bouwnijverheid CAO 2024-2026",
            "sector": "Bouw",
            "company": None,
            "effective_from": "2024-01-01",
            "effective_to": "2026-12-31",
            "coverage_score": 80,
            "document_count": 3,
            "has_salary_scales": True
        }
    ]

    # Filter and score results
    for cao in mock_caos:
        match_score = 0.0
        match_type = "none"

        # Check if CAO is active
        if active_only and cao.get("effective_to"):
            try:
                # Parse date string (handle both date and datetime formats)
                date_str = cao["effective_to"]
                if "T" not in date_str:
                    date_str += "T00:00:00"  # Add time if not present
                end_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                if end_date < datetime.now():
                    continue
            except Exception:
                # If we can't parse the date, include the CAO
                pass

        # Company match (highest priority)
        if company and cao.get("company"):
            if company.lower() in cao["company"].lower():
                match_score = 95.0
                match_type = "company"
            elif cao["company"].lower() in company.lower():
                match_score = 90.0
                match_type = "company_partial"

        # Sector match (more flexible matching)
        if sector and cao.get("sector"):
            sector_match = 0
            sector_lower = sector.lower()
            cao_sector_lower = cao["sector"].lower()

            if sector_lower == cao_sector_lower:
                sector_match = 85.0
                match_type = "sector_exact" if match_type == "none" else match_type
            elif sector_lower in cao_sector_lower or cao_sector_lower in sector_lower:
                # Match both ways for better flexibility
                sector_match = 70.0
                match_type = "sector_partial" if match_type == "none" else match_type
            elif any(word in cao_sector_lower for word in sector_lower.split()):
                # Match individual words for even more flexibility
                sector_match = 65.0
                match_type = "sector_partial" if match_type == "none" else match_type
            elif cao_sector_lower.startswith(sector_lower[:3]) and len(sector_lower) >= 3:
                # Match by prefix (at least 3 chars) for typos or abbreviations
                sector_match = 60.0
                match_type = "sector_partial" if match_type == "none" else match_type

            # If both company and sector match, boost score
            if match_score > 0 and sector_match > 0:
                match_score = min(100, match_score + 5)
            elif sector_match > match_score:
                match_score = sector_match
                match_type = f"sector_{'exact' if sector_match == 85 else 'partial'}"

        # KVK match (would require KVK database integration)
        if kvk:
            # Mock KVK matching
            if kvk == "12345678" and cao.get("company") == "Achmea":
                match_score = 100.0
                match_type = "kvk"

        if match_score > 0:
            results.append(CAOSearchResult(
                id=cao["id"],
                name=cao["name"],
                sector=cao["sector"],
                company=cao.get("company"),
                effective_from=cao["effective_from"],
                effective_to=cao["effective_to"],
                coverage_score=cao["coverage_score"],
                document_count=cao["document_count"],
                has_salary_scales=cao["has_salary_scales"],
                match_type=match_type,
                match_score=match_score
            ))

    # Sort by match score
    results.sort(key=lambda x: x.match_score, reverse=True)

    # Apply pagination
    paginated_results = results[offset:offset + limit]

    # Generate suggestions if no results
    suggestions = []
    if len(results) == 0:
        if company:
            suggestions.append("Try searching by sector instead of company name")
        if sector:
            suggestions.append("Try broader sector terms like 'handel' or 'industrie'")
        suggestions.append("Contact support for manual CAO identification")

    return CAOSearchResponse(
        results=paginated_results,
        total=len(results),
        query={
            "company": company,
            "sector": sector,
            "kvk": kvk
        },
        suggestions=suggestions
    )


@router.get("/sectors", response_model=list[str])
async def list_sectors() -> list[str]:
    """
    Get a list of all available sectors with CAOs.
    Useful for autocomplete and filtering in the UI.
    """
    return [
        "Metalektro",
        "Verzekeringen",
        "Detailhandel",
        "Transport",
        "Groothandel",
        "Bouw",
        "Zorg",
        "Onderwijs",
        "Horeca",
        "ICT",
        "Financiële dienstverlening",
        "Logistiek",
        "Productie",
        "Zakelijke dienstverlening"
    ]


@router.get("/companies", response_model=list[dict[str, str]])
async def search_companies(
    q: str = Query(..., min_length=2, description="Search query for company name")
) -> list[dict[str, str]]:
    """
    Search for companies with known CAOs.
    Returns company names and their KVK numbers for autocomplete.
    """

    # Mock company data
    all_companies = [
        {"name": "Achmea", "kvk": "12345678", "sector": "Verzekeringen"},
        {"name": "IKEA Nederland", "kvk": "23456789", "sector": "Detailhandel"},
        {"name": "Nederlandse Spoorwegen", "kvk": "34567890", "sector": "Transport"},
        {"name": "ING Bank", "kvk": "45678901", "sector": "Financiële dienstverlening"},
        {"name": "Rabobank", "kvk": "56789012", "sector": "Financiële dienstverlening"},
        {"name": "Albert Heijn", "kvk": "67890123", "sector": "Detailhandel"},
        {"name": "KPN", "kvk": "78901234", "sector": "Telecommunicatie"},
        {"name": "PostNL", "kvk": "89012345", "sector": "Logistiek"}
    ]

    # Filter by query
    results = [
        company for company in all_companies
        if q.lower() in company["name"].lower()
    ]

    return results[:10]  # Limit to 10 results