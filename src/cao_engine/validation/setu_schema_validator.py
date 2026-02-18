"""SETU v2.0 Schema Validator using official OpenAPI specification."""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from decimal import Decimal
import jsonschema
from jsonschema import Draft202012Validator
from pydantic import BaseModel


class SchemaValidationError(BaseModel):
    """Represents a schema validation error."""
    path: str
    message: str
    schema_rule: Optional[str] = None
    instance_value: Optional[Any] = None
    severity: str = "error"  # error, warning


class SchemaValidationReport(BaseModel):
    """Complete validation report for SETU document."""
    cao_name: str
    document_id: str
    is_valid: bool
    errors: List[SchemaValidationError] = []
    warnings: List[SchemaValidationError] = []
    coverage_percentage: float = 0.0

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)


class SETUSchemaValidator:
    """Validates SETU JSON against official OpenAPI schema."""

    def __init__(self, schema_path: Optional[Path] = None):
        """Initialize validator with SETU OpenAPI schema."""
        if schema_path is None:
            schema_path = Path(__file__).parent.parent / "models" / "setu_v2_openapi.yaml"

        # Load and parse OpenAPI schema
        with open(schema_path, 'r') as f:
            self.openapi_spec = yaml.safe_load(f)

        # Extract the InquiryPayEquity schema
        self.setu_schema = self._extract_setu_schema()

        # Create JSON Schema validator
        self.validator = Draft202012Validator(self.setu_schema)

        # Required fields from schema
        self.required_fields = self._extract_required_fields()

    def _extract_setu_schema(self) -> Dict:
        """Extract SETU InquiryPayEquity schema from OpenAPI spec."""
        # Get the main schema
        inquiry_schema = self.openapi_spec['components']['schemas']['InquiryPayEquity']

        # Resolve all $ref references
        resolved_schema = self._resolve_refs(inquiry_schema)

        return resolved_schema

    def _resolve_refs(self, schema_part: Any, depth: int = 0) -> Any:
        """Recursively resolve $ref references in schema."""
        if depth > 10:  # Prevent infinite recursion
            return schema_part

        if isinstance(schema_part, dict):
            if '$ref' in schema_part:
                # Resolve reference
                ref_path = schema_part['$ref']
                resolved = self._get_ref_value(ref_path)
                # Continue resolving in the resolved part
                return self._resolve_refs(resolved, depth + 1)
            else:
                # Resolve all values in dict
                return {k: self._resolve_refs(v, depth + 1) for k, v in schema_part.items()}
        elif isinstance(schema_part, list):
            return [self._resolve_refs(item, depth + 1) for item in schema_part]
        else:
            return schema_part

    def _get_ref_value(self, ref_path: str) -> Any:
        """Get value from a $ref path like '#/components/schemas/Something'."""
        if not ref_path.startswith('#/'):
            return {}

        path_parts = ref_path[2:].split('/')
        current = self.openapi_spec

        for part in path_parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return {}

        return current

    def _extract_required_fields(self) -> List[str]:
        """Extract list of required fields from schema."""
        return self.setu_schema.get('required', [])

    def validate(self, setu_data: Dict) -> SchemaValidationReport:
        """Validate SETU data against official schema."""

        report = SchemaValidationReport(
            cao_name=setu_data.get('customer', {}).get('name', 'Unknown'),
            document_id=setu_data.get('documentId', {}).get('value', 'Unknown'),
            is_valid=True
        )

        # 1. Validate against JSON Schema
        errors = list(self.validator.iter_errors(setu_data))

        for error in errors:
            path = '.'.join(str(p) for p in error.absolute_path)

            validation_error = SchemaValidationError(
                path=path or 'root',
                message=error.message,
                schema_rule=error.validator,
                instance_value=error.instance if len(str(error.instance)) < 100 else str(error.instance)[:100] + '...'
            )

            # Classify severity
            if error.validator in ['required', 'type']:
                validation_error.severity = 'error'
                report.errors.append(validation_error)
            else:
                validation_error.severity = 'warning'
                report.warnings.append(validation_error)

        # 2. Check required fields explicitly
        for field in self.required_fields:
            if field not in setu_data:
                report.errors.append(SchemaValidationError(
                    path=field,
                    message=f"Required field '{field}' is missing",
                    schema_rule='required',
                    severity='error'
                ))

        # 3. Validate business rules specific to SETU
        self._validate_business_rules(setu_data, report)

        # 4. Calculate coverage
        report.coverage_percentage = self._calculate_coverage(setu_data)

        # Set overall validity
        report.is_valid = len(report.errors) == 0

        return report

    def _validate_business_rules(self, data: Dict, report: SchemaValidationReport):
        """Validate SETU-specific business rules."""

        # Rule 1: effectivePeriod.validFrom must be before validTo
        if 'effectivePeriod' in data:
            period = data['effectivePeriod']
            if 'validFrom' in period and 'validTo' in period:
                if period['validFrom'] > period['validTo']:
                    report.errors.append(SchemaValidationError(
                        path='effectivePeriod',
                        message='validFrom must be before validTo',
                        schema_rule='business_rule',
                        instance_value=f"{period['validFrom']} > {period['validTo']}"
                    ))

        # Rule 2: Remuneration must have at least one salary scale
        if 'remuneration' in data:
            for i, remun in enumerate(data['remuneration']):
                if 'salaryScale' not in remun or not remun['salaryScale']:
                    report.errors.append(SchemaValidationError(
                        path=f'remuneration[{i}].salaryScale',
                        message='Remuneration must have at least one salary scale',
                        schema_rule='business_rule'
                    ))

        # Rule 3: Salary scales must have valid progression
        if 'remuneration' in data:
            for rem_idx, remun in enumerate(data['remuneration']):
                if 'salaryScale' in remun:
                    for scale_idx, scale in enumerate(remun['salaryScale']):
                        if 'steps' in scale:
                            prev_amount = None
                            for step_idx, step in enumerate(scale['steps']):
                                if 'amount' in step and 'value' in step['amount']:
                                    curr_amount = Decimal(str(step['amount']['value']))
                                    if prev_amount and curr_amount < prev_amount:
                                        report.warnings.append(SchemaValidationError(
                                            path=f'remuneration[{rem_idx}].salaryScale[{scale_idx}].steps[{step_idx}]',
                                            message='Salary step amount decreases',
                                            schema_rule='business_rule',
                                            severity='warning'
                                        ))
                                    prev_amount = curr_amount

    def _calculate_coverage(self, data: Dict) -> float:
        """Calculate percentage of schema fields that are filled."""

        # Define key fields and their weights
        key_fields = {
            'documentId': 10,
            'versionId': 5,
            'issued': 5,
            'effectivePeriod': 10,
            'customer': 10,
            'labourAgreements': 8,
            'positionProfile': 7,
            'remuneration': 15,  # Most important
            'allowance': 8,
            'holidayAllowance': 7,
            'sickPay': 5,
            'leave': 5,
            'pension': 5,
            'individualChoiceBudget': 3,
            'sustainableEmployability': 2
        }

        total_weight = sum(key_fields.values())
        filled_weight = 0

        for field, weight in key_fields.items():
            if field in data and data[field]:
                filled_weight += weight

                # Extra credit for complete remuneration
                if field == 'remuneration':
                    for remun in data['remuneration']:
                        if 'salaryScale' in remun and len(remun['salaryScale']) > 0:
                            filled_weight += 5  # Bonus for having scales

        return min(100.0, (filled_weight / total_weight) * 100)

    def validate_file(self, json_path: Path) -> SchemaValidationReport:
        """Validate a SETU JSON file."""
        with open(json_path, 'r') as f:
            data = json.load(f)

        return self.validate(data)

    def generate_report(self, report: SchemaValidationReport) -> str:
        """Generate human-readable validation report."""

        lines = [
            f"SETU v2.0 Schema Validation Report",
            f"=" * 50,
            f"CAO: {report.cao_name}",
            f"Document ID: {report.document_id}",
            f"Valid: {'✅ YES' if report.is_valid else '❌ NO'}",
            f"Coverage: {report.coverage_percentage:.1f}%",
            f"Errors: {report.error_count}",
            f"Warnings: {report.warning_count}",
            ""
        ]

        if report.errors:
            lines.append("ERRORS:")
            lines.append("-" * 30)
            for error in report.errors[:10]:  # Show first 10
                lines.append(f"  [{error.path}] {error.message}")
                if error.instance_value:
                    lines.append(f"    Value: {error.instance_value}")
            if len(report.errors) > 10:
                lines.append(f"  ... and {len(report.errors) - 10} more errors")
            lines.append("")

        if report.warnings:
            lines.append("WARNINGS:")
            lines.append("-" * 30)
            for warning in report.warnings[:5]:  # Show first 5
                lines.append(f"  [{warning.path}] {warning.message}")
            if len(report.warnings) > 5:
                lines.append(f"  ... and {len(report.warnings) - 5} more warnings")

        return '\n'.join(lines)


def validate_all_setu_files():
    """Validate all SETU files in data/setu directory."""

    validator = SETUSchemaValidator()
    setu_dir = Path("data/setu")

    if not setu_dir.exists():
        print(f"Directory {setu_dir} does not exist")
        return

    json_files = list(setu_dir.glob("*.setu.json"))

    if not json_files:
        print(f"No SETU JSON files found in {setu_dir}")
        return

    print(f"Found {len(json_files)} SETU files to validate")
    print("=" * 50)

    all_reports = []

    for json_file in json_files:
        print(f"\nValidating: {json_file.name}")

        try:
            report = validator.validate_file(json_file)
            all_reports.append(report)

            print(validator.generate_report(report))

            # Save report
            report_file = json_file.parent / f"{json_file.stem}.validation_report.json"
            with open(report_file, 'w') as f:
                f.write(report.model_dump_json(indent=2))

        except Exception as e:
            print(f"  ❌ Error validating {json_file.name}: {e}")

    # Summary
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)

    valid_count = sum(1 for r in all_reports if r.is_valid)
    total_count = len(all_reports)
    avg_coverage = sum(r.coverage_percentage for r in all_reports) / total_count if total_count > 0 else 0

    print(f"Valid files: {valid_count}/{total_count} ({valid_count/total_count*100:.1f}%)")
    print(f"Average coverage: {avg_coverage:.1f}%")
    print(f"Total errors: {sum(r.error_count for r in all_reports)}")
    print(f"Total warnings: {sum(r.warning_count for r in all_reports)}")


if __name__ == "__main__":
    validate_all_setu_files()