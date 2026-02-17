"""Mistral Large Reviewer - Reviews Gemini's SETU extraction.

This is the REVIEWER in the 3-LLM sequential pipeline:
1. Gemini - Extract SETU v2.0 completely (PRIMARY)
2. Mistral Large (this) - Review & find gaps
3. Mistral Small - Judge which output is best
"""

import json
from datetime import datetime
from pathlib import Path

import structlog
from mistralai import Mistral

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
        logger.info("Mistral Large REVIEWER initialized", model=model)

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

        logger.info(
            "Reviewing Gemini extraction with Mistral Large",
            cao=cao_name,
            input_chars=len(text),
            truncated=truncated,
            model=self._model,
        )

        # Build review prompt (SCHEMA REMOVED - too large, causes API hangs)
        prompt = (
            f"{MISTRAL_REVIEWER_PROMPT}\n\n"
            f"GEMINI'S EXTRACTION (to review):\n```json\n{json.dumps(gemini_output, indent=2, ensure_ascii=False)}\n```\n\n"
            f"CAO Name: {cao_name or 'Unknown'}\n\n"
            f"CAO Document (first 100K chars to save tokens):\n\n{text[:100_000]}"
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
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        data = json.loads(content.strip())

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

        logger.info(
            "Mistral REVIEW complete",
            elapsed_seconds=elapsed,
            has_remuneration="remuneration" in data,
            has_allowances="allowances" in data,
            model=self._model,
        )

        return data
