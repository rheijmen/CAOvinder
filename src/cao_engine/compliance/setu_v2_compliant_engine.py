"""
SETU v2.0 Compliant Extraction Engine

This is the GOLD STANDARD engine that ensures all CAO extractions
are fully compliant with SETU v2.0 InquiryPayEquity specification.

It integrates:
1. Official SETU v2.0 schema
2. LLM extraction with correct prompts
3. Automatic transformation to compliant format
4. Validation against official schema
"""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

try:
    from .setu_v2_transformer import SETUv2Transformer
except ImportError:
    from setu_v2_transformer import SETUv2Transformer

logger = structlog.get_logger(__name__)


class ComplianceStatus(Enum):
    """SETU compliance status levels."""
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non_compliant"
    UNKNOWN = "unknown"


class SETUv2CompliantEngine:
    """
    The complete SETU v2.0 compliance engine.

    This engine ensures that CAO information is:
    1. Extracted with the correct SETU v2.0 schema in mind
    2. Transformed to strict SETU v2.0 format
    3. Validated against the official schema
    4. Exported in compliant format
    """

    def __init__(self):
        # Load official SETU v2.0 schema
        self.schema_path = Path(__file__).parent.parent / "models" / "setu_v2_official_schema.json"
        with open(self.schema_path) as f:
            self.official_schema = json.load(f)

        # Initialize transformer
        self.transformer = SETUv2Transformer()

        logger.info("SETU v2.0 Compliant Engine initialized with official schema")

    def get_extraction_prompt(self) -> str:
        """
        Get the GOLD STANDARD extraction prompt that ensures SETU v2.0 compliance.

        This prompt:
        1. Uses the official SETU v2.0 schema structure
        2. Provides clear field mappings
        3. Includes validation rules
        """
        prompt = """You are extracting CAO data for SETU v2.0 InquiryPayEquity format.

CRITICAL: Follow the EXACT structure below. No additional properties allowed!

SETU v2.0 REQUIRED STRUCTURE:

1. documentId (REQUIRED - object, not string!):
   {
     "value": "CAO-[number]-[year]",
     "schemeAgencyId": "CAO"
   }

2. versionId (object, NOT string!):
   {
     "value": "1.0"
   }

3. effectivePeriod (REQUIRED):
   {
     "validFrom": "YYYY-MM-DD",
     "validTo": "YYYY-MM-DD"
   }

4. customer (REQUIRED):
   {
     "name": "Company/Sector name",
     "legalId": [
       {
         "value": "KvK number",
         "schemeAgencyId": "KvK"
       }
     ],
     "personContacts": [
       {
         "name": {
           "formattedName": "Contact Person Name"
         },
         "roleCode": "Authorized"
       }
     ]
   }

5. remuneration (REQUIRED array):
   [{
     "origin": {
       "type": "CollectiveLabourAgreement"
     },
     "workDuration": {
       "amount": 40,  // hours per week
       "interval": {
         "value": 1,
         "unitCode": "Week"
       },
       "valuePerWeek": 40
     },
     "interval": {  // Payment period - OBJECT not string!
       "value": 1,
       "unitCode": "Month"
     },
     "salaryScale": [
       {
         "name": "Scale name",
         "currency": "EUR",  // REQUIRED!
         "minAmount": 2000,
         "maxAmount": 3000,
         "description": "Scale description"
       }
     ]
   }]

6. positionProfile (array - NO additional properties!):
   [{
     "positionId": {"value": "POS001"},
     "positionName": "Function title",
     "description": "Job description"
   }]

7. allowance (NOT "allowances"):
   Use "allowance" for toeslagen

8. leave (NOT "leaveArrangements"):
   Use "leave" for verlof regelingen

CRITICAL RULES:
- NO fields starting with underscore (_extraction_metadata, _compliance)
- NO custom fields (steps, youthScales, aanvang, eind)
- versionId MUST be object {"value": "..."} NOT string
- interval MUST be object {"value": 1, "unitCode": "..."} NOT string
- salaryScale items MUST have "currency": "EUR"
- Use exact field names: "allowance" not "allowances", "leave" not "leaveArrangements"

Extract ONLY what the CAO/inlener offers, NOT statutory minimums.
"""
        return prompt

    def process_extraction(
        self,
        llm_output: dict[str, Any],
        cao_name: str | None = None
    ) -> tuple[dict[str, Any], ComplianceStatus, dict[str, Any]]:
        """
        Process LLM extraction output to ensure SETU v2.0 compliance.

        Args:
            llm_output: Raw output from LLM extraction
            cao_name: Optional CAO name for metadata

        Returns:
            Tuple of:
            - Compliant SETU v2.0 data
            - Compliance status
            - Validation report
        """
        logger.info(f"Processing extraction for SETU v2.0 compliance: {cao_name}")

        # Step 1: Transform to compliant format
        transformed_data = self.transformer.transform(llm_output, preserve_original=True)

        # Step 2: Validate against official schema
        validation_report = self.validate(transformed_data)

        # Step 3: Determine compliance status
        status = self._determine_status(validation_report)

        # Step 4: Export clean version (no metadata)
        compliant_data = self.transformer.export_for_validation(transformed_data)

        logger.info(
            f"Processed extraction: status={status.value}, "
            f"errors={len(validation_report.get('errors', []))}, "
            f"warnings={len(validation_report.get('warnings', []))}"
        )

        return compliant_data, status, validation_report

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Validate data against official SETU v2.0 schema.

        Returns:
            Validation report with errors, warnings, and coverage
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "schema_version": "2.0",
            "errors": [],
            "warnings": [],
            "info": [],
            "coverage": 0.0
        }

        # Clean data for validation (remove metadata)
        clean_data = self.transformer.export_for_validation(data) if hasattr(self, 'transformer') else data

        # Check required fields
        required_fields = self.official_schema.get("required", [])
        for field in required_fields:
            if field not in clean_data:
                report["errors"].append(f"Missing required field: {field}")

        # Check data types
        self._validate_types(clean_data, self.official_schema["properties"], "", report)

        # Check for additional properties
        if not self.official_schema.get("additionalProperties", True):
            valid_props = set(self.official_schema["properties"].keys())
            for key in clean_data.keys():
                if key not in valid_props:
                    report["errors"].append(f"Additional property not allowed: {key}")

        # Calculate coverage
        total_fields = len(self.official_schema["properties"])
        populated_fields = sum(1 for k in self.official_schema["properties"] if k in clean_data)
        report["coverage"] = (populated_fields / total_fields * 100) if total_fields > 0 else 0

        return report

    def _validate_types(self, data: Any, schema: dict, path: str, report: dict):
        """Recursively validate data types against schema."""
        if not isinstance(schema, dict):
            return

        for field, field_schema in schema.items():
            field_path = f"{path}.{field}" if path else field

            if field in data:
                value = data[field]
                expected_type = field_schema.get("type")

                if expected_type == "object":
                    if not isinstance(value, dict):
                        report["errors"].append(
                            f"{field_path}: Expected object, got {type(value).__name__}"
                        )
                    elif "properties" in field_schema:
                        self._validate_types(value, field_schema["properties"], field_path, report)

                elif expected_type == "array":
                    if not isinstance(value, list):
                        report["errors"].append(
                            f"{field_path}: Expected array, got {type(value).__name__}"
                        )
                    elif value and "items" in field_schema:
                        for idx, item in enumerate(value):
                            item_path = f"{field_path}[{idx}]"
                            if "$ref" in field_schema["items"]:
                                # Handle $ref
                                pass
                            elif "properties" in field_schema["items"]:
                                self._validate_types(
                                    item,
                                    field_schema["items"]["properties"],
                                    item_path,
                                    report
                                )

                elif expected_type == "string":
                    if not isinstance(value, str):
                        report["warnings"].append(
                            f"{field_path}: Expected string, got {type(value).__name__}"
                        )

                elif expected_type == "number":
                    if not isinstance(value, (int, float)):
                        report["warnings"].append(
                            f"{field_path}: Expected number, got {type(value).__name__}"
                        )

                elif expected_type == "boolean":
                    if not isinstance(value, bool):
                        report["warnings"].append(
                            f"{field_path}: Expected boolean, got {type(value).__name__}"
                        )

    def _determine_status(self, validation_report: dict[str, Any]) -> ComplianceStatus:
        """Determine compliance status from validation report."""
        errors = validation_report.get("errors", [])
        warnings = validation_report.get("warnings", [])
        coverage = validation_report.get("coverage", 0)

        if not errors and coverage >= 80:
            return ComplianceStatus.COMPLIANT
        elif not errors and coverage >= 50:
            return ComplianceStatus.PARTIAL
        elif errors:
            return ComplianceStatus.NON_COMPLIANT
        else:
            return ComplianceStatus.UNKNOWN

    def save_compliant_output(
        self,
        data: dict[str, Any],
        output_path: Path,
        validation_report: dict[str, Any] | None = None
    ):
        """
        Save SETU v2.0 compliant output.

        Args:
            data: Compliant SETU data
            output_path: Where to save the JSON
            validation_report: Optional validation report to include
        """
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save main data
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Save validation report if provided
        if validation_report:
            report_path = output_path.with_suffix('.validation.json')
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(validation_report, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved compliant SETU v2.0 output to {output_path}")


def get_compliant_engine() -> SETUv2CompliantEngine:
    """Get singleton instance of the compliant engine."""
    if not hasattr(get_compliant_engine, "_instance"):
        get_compliant_engine._instance = SETUv2CompliantEngine()
    return get_compliant_engine._instance


if __name__ == "__main__":
    # Test the engine
    engine = get_compliant_engine()

    # Get extraction prompt
    prompt = engine.get_extraction_prompt()
    print("Extraction Prompt Length:", len(prompt))

    # Test with existing SETU file
    test_file = Path("data/setu/1049-ikea-cao-1-10-2023-tm-31-12-2024-v07022024.setu.json")
    if test_file.exists():
        with open(test_file) as f:
            test_data = json.load(f)

        compliant_data, status, report = engine.process_extraction(test_data, "IKEA CAO")

        print(f"\nCompliance Status: {status.value}")
        print(f"Errors: {len(report.get('errors', []))}")
        print(f"Warnings: {len(report.get('warnings', []))}")
        print(f"Coverage: {report.get('coverage', 0):.1f}%")

        # Save compliant version
        output_path = test_file.with_suffix('.v2compliant.json')
        engine.save_compliant_output(compliant_data, output_path, report)