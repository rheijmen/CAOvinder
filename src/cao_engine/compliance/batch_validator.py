"""
Batch SETU Validator - Validate multiple CAO files and generate comprehensive reports.
"""

import json
from collections import defaultdict
from pathlib import Path

from src.cao_engine.compliance.validators.base_validator import (
    SETUValidator,
    ValidationResult,
)


class BatchValidationReport:
    """Generate comprehensive batch validation reports."""

    def __init__(self, results: list[ValidationResult]):
        self.results = results
        self.total_files = len(results)
        self.valid_files = sum(1 for r in results if r.valid)
        self.invalid_files = self.total_files - self.valid_files
        self.total_errors = sum(r.total_errors for r in results)

    def generate_summary(self) -> str:
        """Generate executive summary."""
        valid_pct = (self.valid_files / self.total_files * 100) if self.total_files > 0 else 0

        summary = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    SETU v2.0 BATCH VALIDATION REPORT                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

📊 EXECUTIVE SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Files Validated:    {self.total_files}
✅ Valid Files:           {self.valid_files} ({valid_pct:.1f}%)
❌ Invalid Files:         {self.invalid_files} ({100-valid_pct:.1f}%)
📋 Total Errors:          {self.total_errors}

"""
        return summary

    def generate_file_details(self) -> str:
        """Generate per-file details."""
        details = "\n📁 FILE-BY-FILE BREAKDOWN\n"
        details += "━" * 80 + "\n\n"

        for result in self.results:
            filename = Path(result.file_path).name
            status = "✅ VALID" if result.valid else f"❌ {result.total_errors} ERRORS"

            details += f"File: {filename}\n"
            details += f"Status: {status}\n"

            if not result.valid:
                details += "Error Breakdown:\n"
                details += f"  • Additional Properties:  {len(result.additional_properties_errors)}\n"
                details += f"  • Missing Required:       {len(result.missing_required_errors)}\n"
                details += f"  • Type Errors:            {len(result.type_errors)}\n"
                details += f"  • Enum Violations:        {len(result.enum_errors)}\n"
                details += f"  • Format Violations:      {len(result.format_errors)}\n"
                details += f"  • Other Errors:           {len(result.other_errors)}\n"

            details += "\n" + "-" * 80 + "\n\n"

        return details

    def generate_error_patterns(self) -> str:
        """Analyze and report error patterns across all files."""
        patterns = "\n🔍 ERROR PATTERN ANALYSIS\n"
        patterns += "━" * 80 + "\n\n"

        # Collect all errors
        all_additional = []
        all_missing = []
        all_type = []
        all_enum = []
        all_format = []

        for result in self.results:
            all_additional.extend(result.additional_properties_errors)
            all_missing.extend(result.missing_required_errors)
            all_type.extend(result.type_errors)
            all_enum.extend(result.enum_errors)
            all_format.extend(result.format_errors)

        # Pattern 1: Additional Properties
        if all_additional:
            patterns += f"⚠️  ADDITIONAL PROPERTIES ({len(all_additional)} instances)\n"
            patterns += "   Most common additional properties:\n"

            # Count occurrences
            property_counts = defaultdict(int)
            for err in all_additional:
                # Extract property name from path
                path_parts = err.path.split('/')
                property_counts[err.path] += 1

            # Top 10
            for path, count in sorted(property_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                patterns += f"   • {path}: {count}x\n"

            patterns += "\n"

        # Pattern 2: Missing Required
        if all_missing:
            patterns += f"❌ MISSING REQUIRED FIELDS ({len(all_missing)} instances)\n"
            patterns += "   Most common missing fields:\n"

            field_counts = defaultdict(int)
            for err in all_missing:
                # Extract field name from message
                if "'" in err.message:
                    field = err.message.split("'")[1]
                    location = err.path
                    field_counts[f"{field} at {location}"] += 1

            # Top 10
            for field, count in sorted(field_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                patterns += f"   • {field}: {count}x\n"

            patterns += "\n"

        # Pattern 3: Type Errors
        if all_type:
            patterns += f"🔢 TYPE ERRORS ({len(all_type)} instances)\n"
            patterns += "   Most common type mismatches:\n"

            type_counts = defaultdict(int)
            for err in all_type:
                type_counts[err.path] += 1

            # Top 10
            for path, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                patterns += f"   • {path}: {count}x\n"

            patterns += "\n"

        # Pattern 4: Enum Violations
        if all_enum:
            patterns += f"📝 ENUM VIOLATIONS ({len(all_enum)} instances)\n"
            patterns += "   Invalid enum values:\n"

            enum_counts = defaultdict(list)
            for err in all_enum:
                # Convert value to string to make it hashable
                value_str = str(err.value) if err.value is not None else "null"
                enum_counts[err.path].append(value_str)

            # Top 10
            for path, values in list(enum_counts.items())[:10]:
                unique_values = set(values)
                patterns += f"   • {path}: {unique_values}\n"

            patterns += "\n"

        # Pattern 5: Format Violations
        if all_format:
            patterns += f"📐 FORMAT VIOLATIONS ({len(all_format)} instances)\n"
            patterns += "   Invalid formats:\n"

            format_counts = defaultdict(int)
            for err in all_format:
                format_counts[err.path] += 1

            # Top 10
            for path, count in sorted(format_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                patterns += f"   • {path}: {count}x\n"

        return patterns

    def generate_recommendations(self) -> str:
        """Generate actionable recommendations."""
        recs = "\n💡 RECOMMENDATIONS\n"
        recs += "━" * 80 + "\n\n"

        # Analyze patterns and suggest fixes
        all_missing = []
        all_additional = []
        all_enum = []
        all_type = []

        for result in self.results:
            all_missing.extend(result.missing_required_errors)
            all_additional.extend(result.additional_properties_errors)
            all_enum.extend(result.enum_errors)
            all_type.extend(result.type_errors)

        priority = 1

        # Rec 1: baseAmount
        baseamount_count = sum(1 for err in all_missing if 'baseAmount' in err.message)
        if baseamount_count > 0:
            recs += f"{priority}. ADD MISSING baseAmount FIELDS ({baseamount_count} instances)\n"
            recs += "   Problem: AmountType requires baseAmount field but it's missing\n"
            recs += "   Solution: Add baseAmount structure to all leave/allowance amounts:\n"
            recs += "   ```python\n"
            recs += "   amount['baseAmount'] = {'unitCode': 'FullTimeEquivalent'}\n"
            recs += "   ```\n\n"
            priority += 1

        # Rec 2: Weekday
        weekday_count = sum(1 for err in all_type if 'weekday' in err.path.lower())
        if weekday_count > 0:
            recs += f"{priority}. FIX WEEKDAY FORMAT ({weekday_count} instances)\n"
            recs += "   Problem: Weekday values are numbers, should be day name strings\n"
            recs += "   Solution: Convert numbers to day names:\n"
            recs += "   ```python\n"
            recs += "   weekday_map = {1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', \n"
            recs += "                  4: 'Thursday', 5: 'Friday', 6: 'Saturday', 7: 'Sunday'}\n"
            recs += "   ```\n\n"
            priority += 1

        # Rec 3: Additional properties in baseDefinition
        basedefinition_count = sum(1 for err in all_additional if 'baseDefinition' in err.path)
        if basedefinition_count > 0:
            recs += f"{priority}. REMOVE EXTRA FIELDS FROM baseDefinition ({basedefinition_count} instances)\n"
            recs += "   Problem: baseDefinition only allows 5 specific fields\n"
            recs += "   Solution: Remove 'description', 'allowances', and other extra fields\n"
            recs += "   Allowed: baseType, remunerationIndicator, holidayAllowanceIndicator,\n"
            recs += "            paidLeaveDayIndicator, allAllowancesIndicator\n\n"
            priority += 1

        # Rec 4: pension.name
        pension_name_count = sum(1 for err in all_missing if 'pension' in err.path and 'name' in err.message)
        if pension_name_count > 0:
            recs += f"{priority}. ADD MISSING pension.name ({pension_name_count} instances)\n"
            recs += "   Problem: Pension items require 'name' field\n"
            recs += "   Solution: Add name field (use description or default):\n"
            recs += "   ```python\n"
            recs += "   pension['name'] = pension.get('description', 'Pension arrangement')\n"
            recs += "   ```\n\n"
            priority += 1

        # Rec 5: Enum violations
        if all_enum:
            recs += f"{priority}. FIX ENUM VIOLATIONS ({len(all_enum)} instances)\n"
            recs += "   Problem: Invalid enum values\n"
            recs += "   Common issues:\n"
            for err in all_enum[:5]:
                recs += f"   • {err.path}: '{err.value}' is invalid\n"
            recs += "   Solution: Replace with valid enum values from schema\n\n"

        return recs

    def save_to_file(self, output_path: Path) -> None:
        """Save complete report to file."""
        report = self.generate_summary()
        report += self.generate_file_details()
        report += self.generate_error_patterns()
        report += self.generate_recommendations()

        report += "\n" + "═" * 80 + "\n"
        report += "END OF REPORT\n"
        report += "═" * 80 + "\n"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"📄 Report saved to: {output_path}")

    def save_json(self, output_path: Path) -> None:
        """Save validation results as JSON for programmatic analysis."""
        data = {
            'summary': {
                'total_files': self.total_files,
                'valid_files': self.valid_files,
                'invalid_files': self.invalid_files,
                'total_errors': self.total_errors
            },
            'results': []
        }

        for result in self.results:
            data['results'].append({
                'file': result.file_path,
                'valid': result.valid,
                'total_errors': result.total_errors,
                'errors_by_type': {
                    'additional_properties': len(result.additional_properties_errors),
                    'missing_required': len(result.missing_required_errors),
                    'type_errors': len(result.type_errors),
                    'enum_errors': len(result.enum_errors),
                    'format_errors': len(result.format_errors),
                    'other_errors': len(result.other_errors)
                },
                'sample_errors': [
                    {
                        'path': err.path,
                        'message': err.message,
                        'type': err.error_type
                    }
                    for err in result.errors[:10]  # First 10 errors per file
                ]
            })

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"📊 JSON report saved to: {output_path}")


def main():
    """Batch validate CAOs and generate reports."""
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║              SETU v2.0 BATCH VALIDATOR - Post-Mortem Analysis               ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝\n")

    # Setup
    schema_path = Path("src/cao_engine/compliance/schemas/setu_v2.0.0-draft.3.json")
    validator = SETUValidator(schema_path)

    # Files to validate
    test_files = [
        Path("data/setu/1049-ikea-FINAL-VALID.setu.json"),
        Path("data/setu/1004-achmea-FINAL-VALID-v2.setu.json"),
        Path("data/setu/315-metalektro-cao-01-06-2024-tm-31-12-2025-v11122024.gemini-VALID.setu.json"),
        Path("data/setu/1055-rabobank-cao-2024-2025-v01102024.gemini-VALID.setu.json"),
    ]

    print(f"🔍 Validating {len(test_files)} CAO files...\n")

    # Validate all
    results = []
    for i, test_file in enumerate(test_files, 1):
        if test_file.exists():
            print(f"[{i}/{len(test_files)}] Validating {test_file.name}...")
            result = validator.validate_file(test_file)
            results.append(result)

            status = "✅ VALID" if result.valid else f"❌ {result.total_errors} errors"
            print(f"         → {status}\n")
        else:
            print(f"[{i}/{len(test_files)}] ❌ File not found: {test_file}")

    # Generate reports
    print("\n📊 Generating reports...\n")

    report = BatchValidationReport(results)

    # Console output
    print(report.generate_summary())
    print(report.generate_file_details())
    print(report.generate_error_patterns())
    print(report.generate_recommendations())

    # Save to files
    output_dir = Path("validation_reports")
    output_dir.mkdir(exist_ok=True)

    report.save_to_file(output_dir / "setu_validation_post_mortem.txt")
    report.save_json(output_dir / "setu_validation_results.json")

    print("\n✅ Post-mortem analysis complete!")


if __name__ == "__main__":
    main()
