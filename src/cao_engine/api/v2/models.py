"""Response models for API v2 documentation."""

from typing import Any

from pydantic import BaseModel, Field


class CAOSearchResult(BaseModel):
    """Single CAO search result."""

    id: str = Field(..., description="Unique CAO identifier", examples=["metalektro-cao"])
    name: str = Field(..., description="CAO display name", examples=["CAO Metalektro 2024-2025"])
    effective_from: str | None = Field(None, description="Effective start date (ISO 8601)", examples=["2024-06-01"])
    effective_to: str | None = Field(None, description="Effective end date (ISO 8601)", examples=["2025-12-31"])
    match_type: str = Field(..., description="How the match was found", examples=["company", "sector"])


class CAOSearchResponse(BaseModel):
    """Response for CAO search endpoint."""

    results: list[CAOSearchResult] = Field(..., description="List of matching CAOs")
    count: int = Field(..., description="Number of results found", examples=[5])
    search: dict[str, str | None] = Field(..., description="Search parameters used")

    model_config = {
        "json_schema_extra": {
            "examples": [{
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
                "search": {
                    "company": None,
                    "sector": "metalektro"
                }
            }]
        }
    }


class CAODetailResponse(BaseModel):
    """Response for CAO detail endpoint."""

    id: str = Field(..., description="CAO identifier")
    documentId: str = Field(..., description="SETU document identifier")
    customer: dict[str, Any] = Field(..., description="Customer/employer information")
    effectivePeriod: dict[str, str] = Field(..., description="Period when CAO is valid")
    version: str = Field(..., description="Document version", examples=["1.0"])
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extraction metadata")


class SalaryScalesResponse(BaseModel):
    """Response for salary scales endpoint."""

    cao_id: str = Field(..., description="CAO identifier")
    salary_scales: list[dict[str, Any]] = Field(..., description="Salary scale definitions")
    wage_components: list[dict[str, Any]] = Field(..., description="Wage component definitions")
    minimum_wage: float | None = Field(None, description="Minimum wage in EUR")
    effective_date: str | None = Field(None, description="Effective date")


class AllowancesResponse(BaseModel):
    """Response for allowances endpoint."""

    cao_id: str = Field(..., description="CAO identifier")
    allowances: list[dict[str, Any]] = Field(..., description="Allowance definitions")
    count: int = Field(..., description="Number of allowances")
    types: list[str] = Field(..., description="Unique allowance types")


class ValidationIssue(BaseModel):
    """Single validation issue."""

    type: str = Field(..., description="Issue type", examples=["minimum_wage_violation"])
    severity: str = Field(..., description="Issue severity", examples=["critical", "warning", "info"])
    message: str = Field(..., description="Human-readable description")
    field: str = Field(..., description="Field that caused the issue")


class PayrollValidationRequest(BaseModel):
    """Request body for payroll validation."""

    cao_id: str = Field(..., description="CAO identifier to validate against", examples=["metalektro-cao"])
    gross_salary: float = Field(..., description="Gross monthly salary in EUR", examples=[3500.00])
    job_level: str | None = Field(None, description="Job level/function group", examples=["Groep 5"])
    allowances: dict[str, float] = Field(default_factory=dict, description="Allowances paid", examples=[{"shift": 250.00, "overtime": 150.00}])

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "cao_id": "metalektro-cao",
                "gross_salary": 3500.00,
                "job_level": "Groep 5",
                "allowances": {
                    "shift": 250.00,
                    "overtime": 150.00
                }
            }]
        }
    }


class PayrollValidationResponse(BaseModel):
    """Response for payroll validation."""

    cao_id: str = Field(..., description="CAO identifier validated against")
    validation_date: str = Field(..., description="Date of validation (ISO 8601)")
    compliant: bool = Field(..., description="Whether payroll is fully compliant")
    issues: list[ValidationIssue] = Field(..., description="List of compliance issues found")
    coverage_score: int = Field(..., description="Compliance coverage score (0-100)")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "cao_id": "metalektro-cao",
                "validation_date": "2025-03-04T10:30:00",
                "compliant": True,
                "issues": [],
                "coverage_score": 95
            }]
        }
    }


class CAOChange(BaseModel):
    """Single CAO change event."""

    id: str = Field(..., description="Change identifier")
    cao_id: str = Field(..., description="CAO identifier")
    type: str = Field(..., description="Change type", examples=["wage_increase", "new_allowance", "amendment"])
    description: str = Field(..., description="Change description")
    effective_date: str = Field(..., description="When change takes effect")
    detected_at: str = Field(..., description="When change was detected")


class ChangesFeedResponse(BaseModel):
    """Response for changes feed endpoint."""

    changes: list[CAOChange] = Field(..., description="List of CAO changes")
    count: int = Field(..., description="Number of changes returned")
    filters: dict[str, Any] = Field(..., description="Applied filters")


class UsageResponse(BaseModel):
    """Response for API usage endpoint."""

    customer_id: str = Field(..., description="Customer identifier")
    key_name: str = Field(..., description="API key name/description")
    calls_this_month: int = Field(..., description="API calls made this month", examples=[1250])
    monthly_limit: int = Field(..., description="Monthly call limit", examples=[10000])
    remaining: int = Field(..., description="Remaining calls this month", examples=[8750])
    last_used: str | None = Field(None, description="Last usage timestamp (ISO 8601)")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "customer_id": "demo_customer",
                "key_name": "Production Key",
                "calls_this_month": 1250,
                "monthly_limit": 10000,
                "remaining": 8750,
                "last_used": "2025-03-04T10:30:00"
            }]
        }
    }


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str = Field(..., description="Error message", examples=["Invalid API key"])

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "detail": "Invalid API key"
            }]
        }
    }
