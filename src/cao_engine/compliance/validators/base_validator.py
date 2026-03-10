"""
Base SETU v2.0 Validator using jsonschema library.

Provides local validation of SETU JSON files against the official schema,
eliminating the need for manual web uploads to semantic-treehouse.nl.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import Draft202012Validator


@dataclass
class ValidationError:
    """Single validation error with path and details."""
    path: str
    message: str
    schema_path: str
    error_type: str  # additionalProperties, required, type, enum, format
    value: Any = None


@dataclass
class ValidationResult:
    """Complete validation result with categorized errors."""
    valid: bool
    file_path: str
    schema_version: str
    total_errors: int
    errors: list[ValidationError] = field(default_factory=list)

    # Categorized errors
    additional_properties_errors: list[ValidationError] = field(default_factory=list)
    missing_required_errors: list[ValidationError] = field(default_factory=list)
    type_errors: list[ValidationError] = field(default_factory=list)
    enum_errors: list[ValidationError] = field(default_factory=list)
    format_errors: list[ValidationError] = field(default_factory=list)
    other_errors: list[ValidationError] = field(default_factory=list)

    def summary(self) -> str:
        """Get human-readable summary."""
        if self.valid:
            return f"✅ {self.file_path}: VALID"

        return f"""❌ {self.file_path}: {self.total_errors} errors
   • Additional properties: {len(self.additional_properties_errors)}
   • Missing required: {len(self.missing_required_errors)}
   • Type errors: {len(self.type_errors)}
   • Enum violations: {len(self.enum_errors)}
   • Format violations: {len(self.format_errors)}
   • Other: {len(self.other_errors)}"""


class SETUValidator:
    """Validates SETU JSON files against official schema."""

    def __init__(self, schema_path: Path):
        """
        Initialize validator with schema.

        Args:
            schema_path: Path to JSON Schema file
        """
        self.schema_path = schema_path
        with open(schema_path, encoding='utf-8') as f:
            self.schema = json.load(f)

        self.validator = Draft202012Validator(self.schema)
        self.schema_version = self.schema.get('_metadata', {}).get('version', 'unknown')

    def validate_file(self, setu_file: Path) -> ValidationResult:
        """
        Validate a SETU JSON file.

        Args:
            setu_file: Path to SETU JSON file to validate

        Returns:
            ValidationResult with all errors categorized
        """
        with open(setu_file, encoding='utf-8') as f:
            data = json.load(f)

        return self.validate_data(data, str(setu_file))

    def validate_data(self, data: dict[str, Any], file_path: str = "data") -> ValidationResult:
        """
        Validate SETU data dict.

        Args:
            data: SETU data dictionary
            file_path: Optional file path for reporting

        Returns:
            ValidationResult with all errors categorized
        """
        errors = list(self.validator.iter_errors(data))

        result = ValidationResult(
            valid=len(errors) == 0,
            file_path=file_path,
            schema_version=self.schema_version,
            total_errors=len(errors)
        )

        # Categorize errors
        for error in errors:
            val_error = self._parse_error(error)
            result.errors.append(val_error)

            # Categorize
            if val_error.error_type == "additionalProperties":
                result.additional_properties_errors.append(val_error)
            elif val_error.error_type == "required":
                result.missing_required_errors.append(val_error)
            elif val_error.error_type == "type":
                result.type_errors.append(val_error)
            elif val_error.error_type == "enum":
                result.enum_errors.append(val_error)
            elif val_error.error_type == "format":
                result.format_errors.append(val_error)
            else:
                result.other_errors.append(val_error)

        return result

    def _parse_error(self, error: jsonschema.ValidationError) -> ValidationError:
        """
        Parse jsonschema ValidationError into our ValidationError format.

        Args:
            error: jsonschema ValidationError

        Returns:
            Our ValidationError with categorization
        """
        # Build JSON path
        path = "/" + "/".join(str(p) for p in error.absolute_path)
        if not path or path == "/":
            path = "/"

        # Build schema path
        schema_path = "/" + "/".join(str(p) for p in error.absolute_schema_path)

        # Determine error type
        error_type = error.validator

        # Get cleaner message
        message = error.message

        return ValidationError(
            path=path,
            message=message,
            schema_path=schema_path,
            error_type=error_type,
            value=error.instance if hasattr(error, 'instance') else None
        )

    def print_errors(self, result: ValidationResult, max_errors: int = 20) -> None:
        """
        Print validation errors in readable format.

        Args:
            result: ValidationResult to print
            max_errors: Maximum number of errors to print per category
        """
        print(result.summary())

        if not result.valid:
            print("\n📋 Error Details:\n")

            # Additional properties
            if result.additional_properties_errors:
                print(f"⚠️  Additional Properties ({len(result.additional_properties_errors)}):")
                for err in result.additional_properties_errors[:max_errors]:
                    print(f"   {err.path}")
                    print(f"      {err.message}")
                if len(result.additional_properties_errors) > max_errors:
                    print(f"   ... and {len(result.additional_properties_errors) - max_errors} more")
                print()

            # Missing required
            if result.missing_required_errors:
                print(f"❌ Missing Required Fields ({len(result.missing_required_errors)}):")
                for err in result.missing_required_errors[:max_errors]:
                    print(f"   {err.path}")
                    print(f"      {err.message}")
                if len(result.missing_required_errors) > max_errors:
                    print(f"   ... and {len(result.missing_required_errors) - max_errors} more")
                print()

            # Type errors
            if result.type_errors:
                print(f"🔢 Type Errors ({len(result.type_errors)}):")
                for err in result.type_errors[:max_errors]:
                    print(f"   {err.path}")
                    print(f"      {err.message}")
                if len(result.type_errors) > max_errors:
                    print(f"   ... and {len(result.type_errors) - max_errors} more")
                print()

            # Enum violations
            if result.enum_errors:
                print(f"📝 Enum Violations ({len(result.enum_errors)}):")
                for err in result.enum_errors[:max_errors]:
                    print(f"   {err.path}")
                    print(f"      {err.message}")
                    print(f"      Current value: {err.value}")
                if len(result.enum_errors) > max_errors:
                    print(f"   ... and {len(result.enum_errors) - max_errors} more")
                print()

            # Format errors
            if result.format_errors:
                print(f"📐 Format Violations ({len(result.format_errors)}):")
                for err in result.format_errors[:max_errors]:
                    print(f"   {err.path}")
                    print(f"      {err.message}")
                    print(f"      Current value: {err.value}")
                if len(result.format_errors) > max_errors:
                    print(f"   ... and {len(result.format_errors) - max_errors} more")
                print()

            # Other errors
            if result.other_errors:
                print(f"❓ Other Errors ({len(result.other_errors)}):")
                for err in result.other_errors[:max_errors]:
                    print(f"   {err.path}")
                    print(f"      {err.message}")
                if len(result.other_errors) > max_errors:
                    print(f"   ... and {len(result.other_errors) - max_errors} more")


def main():
    """Test validator on sample files."""
    schema_path = Path("src/cao_engine/compliance/schemas/setu_v2.0.0-draft.3.json")
    validator = SETUValidator(schema_path)

    # Test files
    test_files = [
        Path("data/setu/1049-ikea-FINAL-VALID.setu.json"),
        Path("data/setu/315-metalektro-cao-01-06-2024-tm-31-12-2025-v11122024.gemini-VALID.setu.json"),
        Path("data/setu/1055-rabobank-cao-2024-2025-v01102024.gemini-VALID.setu.json")
    ]

    for test_file in test_files:
        if test_file.exists():
            print(f"\n{'='*80}")
            print(f"Validating: {test_file.name}")
            print(f"{'='*80}")

            result = validator.validate_file(test_file)
            validator.print_errors(result, max_errors=10)
        else:
            print(f"❌ File not found: {test_file}")


if __name__ == "__main__":
    main()
