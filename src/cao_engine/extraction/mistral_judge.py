"""Mistral Small 2506 Judge - Compares Gemini vs Mistral and decides final SETU output.

This is the JUDGE in the 3-LLM sequential pipeline:
1. Gemini - Extract SETU v2.0 completely (PRIMARY)
2. Mistral Large - Review & find gaps (REVIEWER)
3. Mistral Small 2506 (this) - Judge which output is best (JUDGE)

GOLD STANDARD: Uses SETU Compliance Engine for schema-aware judging.
"""

import json
from datetime import datetime
from pathlib import Path

import structlog
from mistralai import Mistral

try:
    from cao_engine.compliance.setu_compliance_engine import get_compliance_engine
except ImportError:
    # Fallback for module imports
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from compliance.setu_compliance_engine import get_compliance_engine

logger = structlog.get_logger(__name__)

JUDGE_PROMPT = """You are the JUDGE in a 3-LLM pipeline for Dutch CAO SETU v2.0 extraction.

Your task: Compare Gemini's extraction vs Mistral's review and decide the final SETU output.

INPUTS:
1. **Gemini's output** - Primary extraction (1M context, no truncation)
2. **Mistral's output** - Review extraction (500K context, focused review)
3. **Original CAO markdown** - Reference for fact-checking

DECISION CRITERIA:
1. **Completeness** - Which model extracted more fields?
2. **Accuracy** - Which model used correct SETU field names?
3. **Field Mapping** - Which model correctly routed SETU vs Statutory?
4. **Dutch Terminology** - Which model preserved exact CAO terms?
5. **Salary Tables** - Which model correctly parsed HTML tables?

FIELD-BY-FIELD COMPARISON:
For each top-level field, decide:
- Use Gemini's value
- Use Mistral's value
- Merge both (if complementary)
- Use neither (if both wrong)

Provide REASONING for each decision with confidence score (0.0-1.0).

OUTPUT FORMAT:
```json
{
  "final_setu": { /* merged SETU v2.0 */ },
  "judge_report": {
    "total_fields_compared": 127,
    "agreements": 98,
    "gemini_preferred": 21,
    "mistral_preferred": 8,
    "merged": 0,
    "decisions": [
      {
        "field": "remuneration.salaryScale.functiegroepen[0].name",
        "gemini_value": "Functiegroep A",
        "mistral_value": "A",
        "decision": "gemini",
        "confidence": 0.95,
        "reasoning": "Gemini extracted full Dutch term matching CAO source"
      }
    ]
  }
}
```

Be thorough and transparent. Your decisions will be used for legal compliance.
"""


class MistralJudge:
    """Judge that compares Gemini vs Mistral using Mistral Small 2506."""

    def __init__(self, api_key: str, model: str = "mistral-small-2506") -> None:
        self._client = Mistral(api_key=api_key)
        self._model = model

        # Initialize SETU Compliance Engine
        self._compliance_engine = get_compliance_engine()

        logger.info("Mistral Small 2506 JUDGE initialized with SETU Compliance Engine",
                   model=model,
                   setu_version=self._compliance_engine.current_version)

    def judge(
        self,
        gemini_output: dict,
        mistral_output: dict,
        cao_name: str | None = None,
    ) -> dict:
        """Compare Gemini vs Mistral and produce final judged SETU output.

        Args:
            gemini_output: Gemini's primary extraction
            mistral_output: Mistral's review extraction
            cao_name: Optional CAO name for metadata

        Returns:
            Dict with "final_setu" and "judge_report"
        """
        # Get compliance reports for both outputs
        gemini_compliance = gemini_output.get("_compliance", {})
        mistral_compliance = mistral_output.get("_compliance", {})

        logger.info(
            "Judging Gemini vs Mistral with SETU Compliance Engine",
            cao=cao_name,
            model=self._model,
            gemini_compliance=gemini_compliance.get("status", "unknown"),
            gemini_coverage=gemini_compliance.get("coverage", 0),
            mistral_compliance=mistral_compliance.get("status", "unknown"),
            mistral_coverage=mistral_compliance.get("coverage", 0),
        )

        # Build compliance-aware judge prompt
        prompt = (
            f"{JUDGE_PROMPT}\n\n"
            f"COMPLIANCE SCORES:\n"
            f"Gemini: {gemini_compliance.get('status', 'unknown')} ({gemini_compliance.get('coverage', 0):.1f}% coverage)\n"
            f"  Errors: {len(gemini_compliance.get('errors', []))}\n"
            f"  Warnings: {len(gemini_compliance.get('warnings', []))}\n\n"
            f"Mistral: {mistral_compliance.get('status', 'unknown')} ({mistral_compliance.get('coverage', 0):.1f}% coverage)\n"
            f"  Errors: {len(mistral_compliance.get('errors', []))}\n"
            f"  Warnings: {len(mistral_compliance.get('warnings', []))}\n\n"
            f"Use compliance scores to guide your decisions. Higher coverage and fewer errors = better extraction.\n\n"
            f"GEMINI'S EXTRACTION:\n```json\n{json.dumps(gemini_output, indent=2, ensure_ascii=False)}\n```\n\n"
            f"MISTRAL'S REVIEW:\n```json\n{json.dumps(mistral_output, indent=2, ensure_ascii=False)}\n```\n\n"
            f"CAO Name: {cao_name or 'Unknown'}\n\n"
            f"Make your decision field-by-field with reasoning, considering compliance status."
        )

        start_time = datetime.now()
        response = self._client.chat.complete(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.1,
        )
        elapsed = (datetime.now() - start_time).total_seconds()

        # Parse JSON response (clean markdown artifacts if present)
        content = response.choices[0].message.content.strip()

        # Remove markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        # Use a robust method to extract the JSON object, which may have surrounding text.
        try:
            # Find the start of the first JSON object
            json_start_index = content.find('{')
            if json_start_index == -1:
                raise ValueError("No JSON object found in judge response")

            # Use raw_decode to parse the first valid JSON object from the string
            result, _ = json.JSONDecoder().raw_decode(content[json_start_index:])
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Failed to parse JSON from judge response", content=content, error=str(e))
            raise ValueError(f"Could not decode JSON from judge response: {e}") from e

        # Add judge metadata
        if "final_setu" not in result:
            raise ValueError("Judge output missing 'final_setu' field")

        # Validate the final SETU output against compliance engine
        final_status, final_report = self._compliance_engine.validate_extraction(result["final_setu"])

        result["final_setu"]["_extraction_metadata"] = {
            "extractor": "mistral-judge",
            "model": self._model,
            "cao_name": cao_name,
            "extracted_at": datetime.now().isoformat(),
            "elapsed_seconds": elapsed,
            "gemini_version": gemini_output.get("_extraction_metadata", {}).get("extracted_at"),
            "mistral_version": mistral_output.get("_extraction_metadata", {}).get("extracted_at"),
        }

        # Add final compliance metadata
        result["final_setu"]["_compliance"] = {
            "status": final_status.value,
            "coverage": final_report["coverage"],
            "validated_at": datetime.now().isoformat(),
            "setu_version": self._compliance_engine.current_version,
            "errors": final_report.get("errors", []),
            "warnings": final_report.get("warnings", []),
            "source_comparisons": {
                "gemini": {
                    "status": gemini_compliance.get("status", "unknown"),
                    "coverage": gemini_compliance.get("coverage", 0),
                },
                "mistral": {
                    "status": mistral_compliance.get("status", "unknown"),
                    "coverage": mistral_compliance.get("coverage", 0),
                },
            }
        }

        # Add summary stats to report
        if "judge_report" in result:
            result["judge_report"]["metadata"] = {
                "model": self._model,
                "elapsed_seconds": elapsed,
                "final_compliance": final_status.value,
                "final_coverage": final_report["coverage"],
                "judged_at": datetime.now().isoformat(),
            }

        logger.info(
            "Judge decision complete with SETU Compliance validation",
            elapsed_seconds=elapsed,
            total_decisions=result.get("judge_report", {}).get("total_fields_compared", 0),
            gemini_preferred=result.get("judge_report", {}).get("gemini_preferred", 0),
            mistral_preferred=result.get("judge_report", {}).get("mistral_preferred", 0),
            final_compliance=final_status.value,
            final_coverage=final_report["coverage"],
            final_errors=len(final_report.get("errors", [])),
            model=self._model,
        )

        return result
