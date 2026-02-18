"""Mistral Large Reviewer - Reviews Gemini's SETU extraction.

This is the REVIEWER in the 3-LLM sequential pipeline:
1. Gemini - Extract SETU v2.0 completely (PRIMARY)
2. Mistral Large (this) - Review & find gaps
3. Mistral Small - Judge which output is best

GOLD STANDARD: Uses SETU Compliance Engine for schema-aware review.
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

# Load SETU v2.0 schema
SETU_SCHEMA_PATH = Path(__file__).parent.parent / "models" / "setu_v2_schema.json"
SETU_SCHEMA = json.loads(SETU_SCHEMA_PATH.read_text())

MISTRAL_REVIEWER_PROMPT = """You are the REVIEWER in a 3-LLM sequential pipeline for Dutch CAO extraction.

Your task: Review Gemini's SETU extraction and find gaps/issues.

CONTEXT:
- Gemini 2.5 Flash has already extracted SETU v2.0 data from this CAO
- Your job is to CHECK for completeness and correctness
- Extract ANYTHING that Gemini missed or got wrong

REVIEW CHECKLIST:
1. **Salary Scales (Loongebouw)**
   - Did Gemini extract ALL functiegroepen?
   - Did Gemini extract ALL schalen within each functiegroep?
   - Did Gemini extract ALL treden (steps) with correct amounts?
   - Check HTML tables in markdown - often contain critical salary data

2. **Allowances (Toeslagen)**
   - ORT (onregelmatigheidstoeslag)
   - Ploegentoeslag
   - Overwerktoeslag
   - Reiskostenvergoeding
   - Any other allowances mentioned

3. **Leave (Verlof)**
   - Vakantiedagen (vacation days)
   - ADV/ATV dagen
   - Feestdagen (public holidays)
   - Special leave categories

4. **Pension**
   - Employer contribution percentage
   - Pension fund name
   - Any special pension arrangements

5. **Field Mapping**
   - Did Gemini correctly route SETU vs Statutory?
   - Are WML references marked as minimumWage=true flags (NOT extracted amounts)?
   - Are fiscal limits IGNORED (those belong in Statutory)?

OUTPUT FORMAT:
Return ONLY valid JSON - no markdown, no explanation, no code blocks.
Extract a COMPLETE SETU v2.0 JSON with your review.
Include EVERYTHING Gemini found + anything Gemini missed.
Focus on completeness.

You will be compared against Gemini by a judge model.
"""


class MistralReviewer:
    """Reviews Gemini's SETU extraction using Mistral Large."""

    def __init__(self, api_key: str, model: str = "mistral-large-latest") -> None:
        self._client = Mistral(api_key=api_key)
        self._model = model

        # Initialize SETU Compliance Engine
        self._compliance_engine = get_compliance_engine()

        logger.info("Mistral Large REVIEWER initialized with SETU Compliance Engine",
                   model=model,
                   setu_version=self._compliance_engine.current_version)

    def review(
        self,
        markdown: str,
        gemini_output: dict,
        cao_name: str | None = None,
    ) -> dict:
        """Review Gemini's extraction and produce alternative SETU extraction.

        Args:
            markdown: Original CAO markdown (truncated to 500K for Mistral)
            gemini_output: Gemini's SETU extraction to review
            cao_name: Optional CAO name for metadata

        Returns:
            Mistral's SETU v2.0 extraction (incorporating review findings)
        """
        # Truncate markdown to 500K chars (Mistral Large limit)
        text = markdown[:500_000]
        truncated = len(markdown) > 500_000

        # First validate Gemini's extraction to understand gaps
        gemini_status, gemini_report = self._compliance_engine.validate_extraction(gemini_output)

        logger.info(
            "Reviewing Gemini extraction with Mistral Large + Compliance Engine",
            cao=cao_name,
            input_chars=len(text),
            truncated=truncated,
            model=self._model,
            gemini_compliance=gemini_status.value,
            gemini_coverage=gemini_report["coverage"],
            gemini_errors=gemini_report.get("errors", []),
        )

        # Get compliance-aware extraction prompt
        compliance_prompt = self._compliance_engine.generate_extraction_prompt()

        # Build review prompt with compliance insights
        prompt = (
            f"{MISTRAL_REVIEWER_PROMPT}\n\n"
            f"COMPLIANCE GUIDELINES & SCHEMA:\n{compliance_prompt}\n\n"
            f"GEMINI'S COMPLIANCE ISSUES:\n"
            f"- Status: {gemini_status.value}\n"
            f"- Coverage: {gemini_report['coverage']:.1f}%\n"
        )

        if gemini_report.get("errors"):
            prompt += f"- Errors: {', '.join(gemini_report['errors'][:5])}\n"
        if gemini_report.get("warnings"):
            prompt += f"- Warnings: {', '.join(gemini_report['warnings'][:3])}\n"

        prompt += (
            f"\nFOCUS ON FIXING THESE GAPS!\n\n"
            f"GEMINI'S EXTRACTION:\n```json\n{json.dumps(gemini_output, indent=2, ensure_ascii=False)}\n```\n\n"
            f"CAO Name: {cao_name or 'Unknown'}\n\n"
            f"CAO Document (up to 500K chars):\n\n{text}"
        )

        start_time = datetime.now()
        try:
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
        except Exception as e:
            logger.error("Mistral API call failed during review", error=str(e))
            raise
        elapsed = (datetime.now() - start_time).total_seconds()

        # Parse JSON response (clean markdown artifacts if present)
        content = response.choices[0].message.content.strip()

        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        try:
            json_start_index = content.find('{')
            if json_start_index == -1:
                raise ValueError("No JSON object found in reviewer response")
            data, _ = json.JSONDecoder().raw_decode(content[json_start_index:])
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Failed to parse JSON from reviewer response", content=content, error=str(e))
            raise ValueError(f"Could not decode JSON from reviewer response: {e}") from e

        # Validate Mistral's extraction against SETU schema
        mistral_status, mistral_report = self._compliance_engine.validate_extraction(data)

        # Add review metadata
        data["_extraction_metadata"] = {
            "extractor": "mistral-reviewer",
            "model": self._model,
            "cao_name": cao_name,
            "extracted_at": datetime.now().isoformat(),
            "input_chars": len(text),
            "truncated": truncated,
            "elapsed_seconds": elapsed,
            "reviewed_gemini_version": gemini_output.get("_extraction_metadata", {}).get("extracted_at"),
        }

        # Add compliance metadata
        data["_compliance"] = {
            "status": mistral_status.value,
            "coverage": mistral_report["coverage"],
            "validated_at": datetime.now().isoformat(),
            "setu_version": self._compliance_engine.current_version,
            "errors": mistral_report.get("errors", []),
            "warnings": mistral_report.get("warnings", []),
            "improvement_over_gemini": {
                "coverage_delta": mistral_report["coverage"] - gemini_report["coverage"],
                "errors_delta": len(mistral_report.get("errors", [])) - len(gemini_report.get("errors", [])),
            }
        }

        logger.info(
            "Mistral REVIEW complete with compliance validation",
            elapsed_seconds=elapsed,
            has_remuneration="remuneration" in data,
            has_allowances="allowances" in data,
            compliance_status=mistral_status.value,
            coverage=mistral_report["coverage"],
            improvement=data["_compliance"]["improvement_over_gemini"]["coverage_delta"],
            model=self._model,
        )

        return data
