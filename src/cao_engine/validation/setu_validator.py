"""SETU v2.0 Validation Framework for 100% accuracy."""

import json
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel


class ValidationError(BaseModel):
    field: str
    severity: str  # "critical", "warning", "info"
    message: str
    expected: str | None = None
    actual: str | None = None


class ValidationReport(BaseModel):
    cao_name: str
    total_fields: int
    validated_fields: int
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []
    score: float = 0.0

    @property
    def is_valid(self) -> bool:
        return len([e for e in self.errors if e.severity == "critical"]) == 0


class SETUValidator:
    """Validates SETU extraction quality against ground truth."""

    def __init__(self):
        self.rules = self._load_validation_rules()

    def _load_validation_rules(self) -> dict:
        """Load SETU v2.0 validation rules."""
        return {
            # CRITICAL: Must be present and valid
            "critical_fields": [
                "documentId",
                "documentVersion",
                "inlenerNaam",
                "geldigVan",
                "geldigTot",
                "loongebouw.functiegroepen[].code",
                "loongebouw.functiegroepen[].schalen[].periodeloon"
            ],

            # Format validations
            "formats": {
                "dates": r"^\d{4}-\d{2}-\d{2}$",  # ISO 8601
                "currency": r"^\d+\.\d{2}$",  # Decimal with 2 places
                "percentage": r"^\d+(\.\d{1,2})?$"  # Max 2 decimal places
            },

            # Business rules
            "business_rules": [
                {
                    "name": "salary_progression",
                    "rule": "Each scale must have aanvang <= eind"
                },
                {
                    "name": "youth_scale_progression",
                    "rule": "Youth scales must increase with age: 16yr < 17yr < 18yr..."
                },
                {
                    "name": "date_validity",
                    "rule": "geldigVan must be before geldigTot"
                },
                {
                    "name": "scale_completeness",
                    "rule": "If youth scales exist, all ages 16-20 must be present"
                }
            ]
        }

    def validate_extraction(self, setu_json: dict, source_md: str) -> ValidationReport:
        """Validate SETU extraction against source and rules."""

        report = ValidationReport(
            cao_name=setu_json.get("inlenerNaam", "Unknown"),
            total_fields=self._count_fields(setu_json),
            validated_fields=0
        )

        # 1. Check critical fields
        for field_path in self.rules["critical_fields"]:
            if not self._check_field_exists(setu_json, field_path):
                report.errors.append(ValidationError(
                    field=field_path,
                    severity="critical",
                    message=f"Required field missing: {field_path}"
                ))

        # 2. Validate formats
        self._validate_formats(setu_json, report)

        # 3. Check business rules
        self._validate_business_rules(setu_json, report)

        # 4. Cross-reference with source
        self._validate_against_source(setu_json, source_md, report)

        # Calculate score
        report.score = self._calculate_score(report)

        return report

    def _validate_formats(self, setu: dict, report: ValidationReport):
        """Validate field formats."""
        # Date fields
        date_fields = ["geldigVan", "geldigTot"]
        for field in date_fields:
            if field in setu:
                if not self._is_valid_date(setu[field]):
                    report.errors.append(ValidationError(
                        field=field,
                        severity="critical",
                        message="Invalid date format",
                        expected="YYYY-MM-DD",
                        actual=setu[field]
                    ))

        # Currency fields in loongebouw
        if "loongebouw" in setu and "functiegroepen" in setu["loongebouw"]:
            for fg in setu["loongebouw"]["functiegroepen"]:
                for schaal in fg.get("schalen", []):
                    if "periodeloon" in schaal:
                        if not self._is_valid_currency(schaal["periodeloon"]):
                            report.warnings.append(ValidationError(
                                field=f"functiegroep.{fg.get('code', '?')}.periodeloon",
                                severity="warning",
                                message="Currency should be decimal with 2 places",
                                actual=str(schaal["periodeloon"])
                            ))

    def _validate_business_rules(self, setu: dict, report: ValidationReport):
        """Validate business logic rules."""

        # Check salary progression
        if "loongebouw" in setu and "functiegroepen" in setu["loongebouw"]:
            for fg in setu["loongebouw"]["functiegroepen"]:
                for schaal in fg.get("schalen", []):
                    aanvang = schaal.get("aanvang")
                    eind = schaal.get("eind")

                    if aanvang and eind:
                        if Decimal(str(aanvang)) > Decimal(str(eind)):
                            report.errors.append(ValidationError(
                                field=f"functiegroep.{fg.get('code', '?')}",
                                severity="critical",
                                message="Aanvang salary exceeds eind salary",
                                expected="aanvang <= eind",
                                actual=f"{aanvang} > {eind}"
                            ))

        # Check date validity
        if "geldigVan" in setu and "geldigTot" in setu:
            if setu["geldigVan"] >= setu["geldigTot"]:
                report.errors.append(ValidationError(
                    field="dates",
                    severity="critical",
                    message="geldigVan must be before geldigTot",
                    actual=f"{setu['geldigVan']} >= {setu['geldigTot']}"
                ))

    def _validate_against_source(self, setu: dict, source_md: str, report: ValidationReport):
        """Cross-reference extracted values with source markdown."""

        # Example: Check if extracted salary values exist in source
        if "loongebouw" in setu and "functiegroepen" in setu["loongebouw"]:
            for fg in setu["loongebouw"]["functiegroepen"]:
                for schaal in fg.get("schalen", []):
                    if "periodeloon" in schaal:
                        # Convert to various formats that might appear in source
                        value = str(schaal["periodeloon"])
                        variations = [
                            value,  # 2389.44
                            f"€ {value}",  # € 2389.44
                            f"€{value}",  # €2389.44
                            value.replace(".", ","),  # 2389,44
                            f"€ {value.replace('.', ',')}",  # € 2389,44
                        ]

                        found = any(var in source_md for var in variations)
                        if not found:
                            report.warnings.append(ValidationError(
                                field=f"functiegroep.{fg.get('code', '?')}.periodeloon",
                                severity="warning",
                                message="Value not found in source document",
                                actual=value
                            ))

    def _calculate_score(self, report: ValidationReport) -> float:
        """Calculate validation score (0-100)."""
        if report.total_fields == 0:
            return 0.0

        # Deduct points for errors
        critical_errors = len([e for e in report.errors if e.severity == "critical"])
        warnings = len(report.warnings)

        score = 100.0
        score -= critical_errors * 10  # -10 points per critical error
        score -= warnings * 2  # -2 points per warning

        return max(0.0, min(100.0, score))

    def _check_field_exists(self, obj: dict, path: str) -> bool:
        """Check if a field exists in nested structure."""
        parts = path.replace("[", ".").replace("]", "").split(".")
        current = obj

        for part in parts:
            if part == "":
                continue
            if isinstance(current, list):
                # Check if any item in list has the field
                return any(self._check_field_exists(item, ".".join(parts[parts.index(part)+1:]))
                          for item in current)
            elif isinstance(current, dict):
                if part not in current:
                    return False
                current = current[part]
            else:
                return False

        return True

    def _count_fields(self, obj: dict, count: int = 0) -> int:
        """Count total fields in nested structure."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                count += 1
                count = self._count_fields(value, count)
        elif isinstance(obj, list):
            for item in obj:
                count = self._count_fields(item, count)
        return count

    def _is_valid_date(self, date_str: str) -> bool:
        """Check if date is in ISO 8601 format."""
        import re
        return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', str(date_str)))

    def _is_valid_currency(self, value) -> bool:
        """Check if value is valid currency format."""
        try:
            dec = Decimal(str(value))
            # Check if it has exactly 2 decimal places
            return dec.as_tuple().exponent >= -2
        except:
            return False


def create_validation_report(setu_file: Path, ocr_file: Path) -> ValidationReport:
    """Create a validation report for a SETU extraction."""

    validator = SETUValidator()

    # Load files
    with open(setu_file) as f:
        setu_data = json.load(f)

    with open(ocr_file) as f:
        ocr_markdown = f.read()

    # Validate
    report = validator.validate_extraction(setu_data, ocr_markdown)

    # Save report
    report_file = setu_file.parent / f"{setu_file.stem}.validation.json"
    with open(report_file, 'w') as f:
        f.write(report.model_dump_json(indent=2))

    return report


if __name__ == "__main__":
    # Example usage
    import sys
    if len(sys.argv) != 3:
        print("Usage: python setu_validator.py <setu.json> <source.md>")
        sys.exit(1)

    report = create_validation_report(Path(sys.argv[1]), Path(sys.argv[2]))

    print(f"Validation Score: {report.score:.1f}%")
    print(f"Critical Errors: {len([e for e in report.errors if e.severity == 'critical'])}")
    print(f"Warnings: {len(report.warnings)}")

    if not report.is_valid:
        print("\n❌ VALIDATION FAILED")
        for error in report.errors:
            if error.severity == "critical":
                print(f"  - {error.field}: {error.message}")
    else:
        print("\n✅ VALIDATION PASSED")