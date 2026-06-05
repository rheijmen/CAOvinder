"""
Compare validation results between Gemini-only and 3-LLM pipeline extractions.

This script validates SETU files from both extraction methods and generates
a comparison report showing the quality improvement from the 3-LLM pipeline.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from .validators.base_validator import SETUValidator, ValidationResult


@dataclass
class PipelineComparison:
    """Comparison between two extraction pipelines."""
    cao_name: str
    gemini_only_file: str
    three_llm_file: str
    gemini_errors: int
    three_llm_errors: int
    error_reduction: int
    error_reduction_percent: float
    gemini_result: ValidationResult
    three_llm_result: ValidationResult


class PipelineComparisonReport:
    """Generate comparison reports between extraction pipelines."""

    def __init__(self, schema_path: Path):
        self.validator = SETUValidator(schema_path)
        self.comparisons: list[PipelineComparison] = []

    def compare_cao(
        self,
        cao_name: str,
        gemini_file: Path,
        three_llm_file: Path
    ) -> PipelineComparison:
        """Compare two extraction outputs for the same CAO."""
        gemini_result = self.validator.validate_file(gemini_file)
        three_llm_result = self.validator.validate_file(three_llm_file)

        error_reduction = gemini_result.total_errors - three_llm_result.total_errors
        error_reduction_percent = (
            (error_reduction / gemini_result.total_errors * 100)
            if gemini_result.total_errors > 0
            else 0.0
        )

        comparison = PipelineComparison(
            cao_name=cao_name,
            gemini_only_file=gemini_file.name,
            three_llm_file=three_llm_file.name,
            gemini_errors=gemini_result.total_errors,
            three_llm_errors=three_llm_result.total_errors,
            error_reduction=error_reduction,
            error_reduction_percent=error_reduction_percent,
            gemini_result=gemini_result,
            three_llm_result=three_llm_result
        )

        self.comparisons.append(comparison)
        return comparison

    def generate_text_report(self) -> str:
        """Generate a human-readable comparison report."""
        lines = []
        lines.append("╔" + "═" * 78 + "╗")
        lines.append("║" + " SETU EXTRACTION PIPELINE COMPARISON ".center(78) + "║")
        lines.append("╚" + "═" * 78 + "╝")
        lines.append("")

        # Executive summary
        total_gemini_errors = sum(c.gemini_errors for c in self.comparisons)
        total_3llm_errors = sum(c.three_llm_errors for c in self.comparisons)
        total_reduction = total_gemini_errors - total_3llm_errors
        avg_reduction_percent = (
            (total_reduction / total_gemini_errors * 100)
            if total_gemini_errors > 0
            else 0.0
        )

        lines.append("📊 EXECUTIVE SUMMARY")
        lines.append("━" * 80)
        lines.append(f"Total CAOs Compared:       {len(self.comparisons)}")
        lines.append(f"Gemini-Only Total Errors:  {total_gemini_errors}")
        lines.append(f"3-LLM Pipeline Total Errors: {total_3llm_errors}")
        lines.append(f"Error Reduction:           {total_reduction} ({avg_reduction_percent:.1f}%)")
        lines.append("")

        # Per-CAO comparison
        lines.append("📁 CAO-BY-CAO COMPARISON")
        lines.append("━" * 80)

        for comp in self.comparisons:
            lines.append(f"\n{comp.cao_name}")
            lines.append(f"  Gemini-Only:  {comp.gemini_errors} errors ({comp.gemini_only_file})")
            lines.append(f"  3-LLM Pipeline: {comp.three_llm_errors} errors ({comp.three_llm_file})")
            lines.append(f"  Improvement:   {comp.error_reduction} fewer errors ({comp.error_reduction_percent:.1f}% reduction)")

            if comp.gemini_errors > 0 and comp.three_llm_errors == 0:
                lines.append("  Status:       ✅ FIXED - Now 100% valid!")
            elif comp.error_reduction > 0:
                lines.append(f"  Status:       ✅ IMPROVED - {comp.error_reduction_percent:.1f}% better")
            elif comp.error_reduction == 0:
                lines.append("  Status:       ⚠️  NO CHANGE")
            else:
                lines.append("  Status:       ❌ REGRESSION")

        lines.append("")

        # Error category breakdown
        lines.append("🔍 ERROR CATEGORY BREAKDOWN")
        lines.append("━" * 80)

        categories = [
            ("Additional Properties", "additional_properties_errors"),
            ("Missing Required Fields", "missing_required_errors"),
            ("Type Errors", "type_errors"),
            ("Enum Violations", "enum_violations"),
            ("Format Violations", "format_violations"),
            ("Other Errors", "other_errors")
        ]

        for category_name, attr_name in categories:
            gemini_count = sum(
                len(getattr(c.gemini_result, attr_name))
                for c in self.comparisons
            )
            three_llm_count = sum(
                len(getattr(c.three_llm_result, attr_name))
                for c in self.comparisons
            )
            reduction = gemini_count - three_llm_count

            if gemini_count > 0 or three_llm_count > 0:
                lines.append(f"\n{category_name}:")
                lines.append(f"  Gemini-Only:    {gemini_count}")
                lines.append(f"  3-LLM Pipeline: {three_llm_count}")
                lines.append(f"  Reduction:      {reduction} ({reduction/gemini_count*100:.1f}%)" if gemini_count > 0 else "  Reduction:      0")

        lines.append("")
        lines.append("═" * 80)
        lines.append("END OF COMPARISON REPORT")
        lines.append("═" * 80)

        return "\n".join(lines)

    def save_json_report(self, output_path: Path):
        """Save comparison data as JSON."""
        data = {
            "total_caos": len(self.comparisons),
            "total_gemini_errors": sum(c.gemini_errors for c in self.comparisons),
            "total_3llm_errors": sum(c.three_llm_errors for c in self.comparisons),
            "comparisons": [
                {
                    "cao_name": c.cao_name,
                    "gemini_only": {
                        "file": c.gemini_only_file,
                        "total_errors": c.gemini_errors,
                        "error_breakdown": {
                            "additional_properties": len(c.gemini_result.additional_properties_errors),
                            "missing_required": len(c.gemini_result.missing_required_errors),
                            "type_errors": len(c.gemini_result.type_errors),
                            "enum_violations": len(c.gemini_result.enum_violations),
                            "format_violations": len(c.gemini_result.format_violations),
                            "other_errors": len(c.gemini_result.other_errors)
                        }
                    },
                    "three_llm": {
                        "file": c.three_llm_file,
                        "total_errors": c.three_llm_errors,
                        "error_breakdown": {
                            "additional_properties": len(c.three_llm_result.additional_properties_errors),
                            "missing_required": len(c.three_llm_result.missing_required_errors),
                            "type_errors": len(c.three_llm_result.type_errors),
                            "enum_violations": len(c.three_llm_result.enum_violations),
                            "format_violations": len(c.three_llm_result.format_violations),
                            "other_errors": len(c.three_llm_result.other_errors)
                        }
                    },
                    "improvement": {
                        "error_reduction": c.error_reduction,
                        "error_reduction_percent": c.error_reduction_percent
                    }
                }
                for c in self.comparisons
            ]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    """Compare Metalektro and Rabobank: Gemini-only vs 3-LLM pipeline."""
    schema_path = Path(__file__).parent / "schemas" / "setu_v2.0.0-draft.3.json"
    setu_dir = Path(__file__).parent.parent.parent.parent / "data" / "setu"

    comparator = PipelineComparisonReport(schema_path)

    # Metalektro comparison
    metalektro_gemini = setu_dir / "315-metalektro-cao-01-06-2024-tm-31-12-2025-v11122024.gemini-VALID.setu.json"
    metalektro_3llm = setu_dir / "315-metalektro-cao-01-06-2024-tm-31-12-2025-v11122024.setu.json"

    if metalektro_gemini.exists() and metalektro_3llm.exists():
        comparator.compare_cao("Metalektro", metalektro_gemini, metalektro_3llm)

    # Rabobank comparison
    rabobank_gemini = setu_dir / "1055-rabobank-cao-2024-2025-v01102024.gemini-VALID.setu.json"
    rabobank_3llm = setu_dir / "1055-rabobank-cao-2024-2025-v01102024.setu.json"

    if rabobank_gemini.exists() and rabobank_3llm.exists():
        comparator.compare_cao("Rabobank", rabobank_gemini, rabobank_3llm)

    # Generate reports
    print(comparator.generate_text_report())

    output_dir = Path(__file__).parent.parent.parent.parent / "validation_reports"
    output_dir.mkdir(exist_ok=True)

    comparator.save_json_report(output_dir / "pipeline_comparison.json")

    with open(output_dir / "pipeline_comparison.txt", 'w', encoding='utf-8') as f:
        f.write(comparator.generate_text_report())


if __name__ == "__main__":
    main()
