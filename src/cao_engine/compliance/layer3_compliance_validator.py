"""
Layer 3: Compliance Validator
==============================
Validate SETU data against official SETU v2.0.0-draft.3 schema.

This is the THIRD layer in our 4-layer compliance system.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog
from jsonschema import Draft202012Validator

logger = structlog.get_logger(__name__)


@dataclass
class ValidationReport:
    """Detailed validation report."""

    total_errors: int
    critical_errors: int
    fixable_errors: int
    semantic_errors: int
    errors: list[dict[str, Any]]
    compliance_score: float  # 0.0 to 1.0

    def is_compliant(self) -> bool:
        """Check if fully compliant (0 errors)."""
        return self.total_errors == 0

    def needs_human_review(self) -> bool:
        """Check if human review needed (semantic errors)."""
        return self.semantic_errors > 0


class ComplianceValidator:
    """
    Layer 3: Validate SETU data for compliance.

    Goal: Catch ALL non-compliance issues
    Output: Detailed validation report
    """

    def __init__(self):
        # Load official SETU schema
        schema_path = Path(__file__).parent / "schemas" / "setu_v2.0.0-draft.3.json"
        with open(schema_path) as f:
            self.schema = json.load(f)

        self.validator = Draft202012Validator(self.schema)

        # Baseline for scoring (Achmea has 171 errors initially)
        self.baseline_error_count = 171

    def validate(self, setu_data: dict[str, Any]) -> ValidationReport:
        """
        Validate SETU data against official schema.

        Returns detailed report with error categorization.
        """
        logger.info("Validating SETU data against official schema")

        errors = []
        for error in self.validator.iter_errors(setu_data):
            error_dict = {
                "message": error.message,
                "path": "/".join(str(p) for p in error.path),
                "schema_path": "/".join(str(p) for p in error.schema_path),
                "validator": error.validator,
                "category": self._categorize_error(error)
            }
            errors.append(error_dict)

        # Categorize errors
        critical = [e for e in errors if e["category"] == "critical"]
        fixable = [e for e in errors if e["category"] == "fixable"]
        semantic = [e for e in errors if e["category"] == "semantic"]

        # Calculate compliance score (0 = worst, 1 = perfect)
        compliance_score = max(0, 1 - (len(errors) / self.baseline_error_count))

        report = ValidationReport(
            total_errors=len(errors),
            critical_errors=len(critical),
            fixable_errors=len(fixable),
            semantic_errors=len(semantic),
            errors=errors,
            compliance_score=compliance_score
        )

        logger.info(
            "Validation complete",
            total_errors=report.total_errors,
            critical=report.critical_errors,
            fixable=report.fixable_errors,
            semantic=report.semantic_errors,
            compliance_score=f"{report.compliance_score:.1%}"
        )

        return report

    def _categorize_error(self, error) -> str:
        """
        Categorize error type for remediation.

        Returns: "critical", "fixable", or "semantic"
        """
        validator_type = error.validator
        path = "/".join(str(p) for p in error.path)
        message = error.message

        # Critical: Missing required fields
        if validator_type == "required":
            return "critical"

        # Fixable: Type mismatches, additional properties
        if validator_type in ["type", "additionalProperties", "enum"]:
            return "fixable"

        # Semantic: Complex structure issues
        if "holidayAllowance" in path or "pension" in path:
            if "origin" in message or "line" in message:
                return "semantic"

        # Default to fixable
        return "fixable"

    def compare_to_baseline(self, report: ValidationReport) -> dict[str, Any]:
        """
        Compare current validation to baseline (Achmea 171 errors).

        Returns improvement metrics.
        """
        improvement = {
            "baseline_errors": self.baseline_error_count,
            "current_errors": report.total_errors,
            "errors_fixed": self.baseline_error_count - report.total_errors,
            "improvement_percentage": (self.baseline_error_count - report.total_errors) / self.baseline_error_count * 100,
            "compliance_score": report.compliance_score
        }

        logger.info(
            "Comparison to baseline",
            baseline=self.baseline_error_count,
            current=report.total_errors,
            improvement=f"{improvement['improvement_percentage']:.1f}%"
        )

        return improvement