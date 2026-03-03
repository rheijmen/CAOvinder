"""Gemini 2.5 Flash Primary SETU Extractor - First pass extraction.

This is the PRIMARY extractor in the 3-LLM sequential pipeline:
1. Gemini (this) - Extract SETU v2.0 completely
2. Mistral Large - Review & find gaps
3. Mistral Small - Judge which output is best
"""

import json
from datetime import datetime
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

# Load SETU v2.0 schema
SETU_SCHEMA_PATH = Path(__file__).parent.parent / "models" / "setu_v2_schema.json"
_SETU_SCHEMA_RAW = json.loads(SETU_SCHEMA_PATH.read_text())

# Strip JSON Schema metadata fields that Gemini doesn't support
SETU_SCHEMA = {k: v for k, v in _SETU_SCHEMA_RAW.items() if k not in ("$schema", "$id")}

# Import field mapping rules
FIELD_MAPPING_PATH = Path(__file__).parent.parent.parent / ".claude" / "skills" / "llm-field-mapping.md"
FIELD_MAPPING_RULES = FIELD_MAPPING_PATH.read_text() if FIELD_MAPPING_PATH.exists() else ""

GEMINI_PRIMARY_PROMPT = f"""You are the PRIMARY extractor in a 3-LLM pipeline for Dutch CAO documents.

Your task: Extract COMPLETE SETU v2.0 InquiryPayEquity data from this CAO.

CRITICAL ROUTING RULE - Store separately, compare at read time, NEVER merge:
- SETU = what the inlener OFFERS (CAO conditions, salary scales, allowances, leave days)
- Statutory = what the government MANDATES (WML, SV-premies, fiscal limits, AOW age)
- Extract ONLY what the inlener offers. IGNORE statutory minimum wages, social insurance premiums, fiscal exemptions.

FIELD MAPPING RULES (150+ aliases):
{FIELD_MAPPING_RULES[:5000] if FIELD_MAPPING_RULES else "See skills/llm-field-mapping.md"}

EXTRACT COMPLETELY:
- ALL functiegroepen (job groups), schalen (scales), treden (steps), amounts from salary tables
- ALL toeslagen (ORT, ploegentoeslag, overwerktoeslag, reiskostenvergoeding, etc.)
- Vakantietoeslag (holiday allowance) percentage and payment moment
- ADV days, public holidays, special leave (in correct leave subcategories)
- Pension schemes as offered by the inlener
- IKB, duurzame inzetbaarheid, generatiepact
- Use EXACT Dutch terminology from the CAO
- For unknown fields: null (NOT empty strings)
- Pay special attention to HTML tables in markdown - they contain critical salary data

Your output will be REVIEWED by Mistral Large and JUDGED by Mistral Small 2506.
Be thorough and complete. Missing data will be flagged by reviewers.

Output MUST be valid SETU v2.0 InquiryPayEquity JSON.

Be thorough. This is for legal compliance in the Dutch staffing industry.
"""


class GeminiPrimaryExtractor:
    """Primary SETU v2.0 extractor using Gemini 2.5 Flash with full 1M context."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self._model = genai.GenerativeModel(
                model_name=model,
                generation_config={
                    "temperature": 0.1,  # Low for factual extraction
                    "response_mime_type": "application/json",
                },
            )
            self._model_name = model
            logger.info(
                "Gemini 2.5 Flash PRIMARY extractor initialized",
                model=model,
            )
        except ImportError as e:
            raise ImportError(
                "google-generativeai package required. Install with: pip install google-generativeai"
            ) from e

    def extract(self, markdown: str, cao_name: str | None = None) -> dict:
        """Extract SETU v2.0 from CAO markdown using full 1M context (no truncation).

        Args:
            markdown: Full OCR markdown text (up to 1M tokens)
            cao_name: Optional CAO name for metadata

        Returns:
            SETU v2.0 InquiryPayEquity JSON dict
        """
        input_chars = len(markdown)
        logger.info(
            "Extracting SETU v2.0 with Gemini 2.5 Flash (PRIMARY)",
            cao=cao_name,
            input_chars=input_chars,
            model=self._model_name,
        )

        # Build prompt with full schema and full CAO text (1M context!)
        prompt = (
            f"{GEMINI_PRIMARY_PROMPT}\n\n"
            f"SETU v2.0 Schema (follow this structure exactly):\n```json\n{json.dumps(SETU_SCHEMA, indent=2)}\n```\n\n"
            f"CAO Name: {cao_name or 'Unknown'}\n\n"
            f"COMPLETE CAO Document (Markdown from Mistral OCR):\n\n{markdown}"
        )

        start_time = datetime.now()
        response = self._model.generate_content(prompt)
        elapsed = (datetime.now() - start_time).total_seconds()

        # Gemini returns JSON when response_mime_type is set to application/json
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.error(f"Response text preview: {response.text[:500]}...")
            # Return a minimal valid SETU structure on error
            data = {
                "documentId": f"error-{datetime.now().isoformat()}",
                "versionCode": "1.0",
                "creationDateTime": datetime.now().isoformat(),
                "inlener": {"name": cao_name or "Unknown"},
                "_error": str(e),
                "_raw_response": response.text[:5000]  # Keep first 5000 chars for debugging
            }

        # Add extraction metadata
        data["_extraction_metadata"] = {
            "extractor": "gemini-primary",
            "model": self._model_name,
            "cao_name": cao_name,
            "extracted_at": datetime.now().isoformat(),
            "input_chars": input_chars,
            "elapsed_seconds": elapsed,
        }

        logger.info(
            "Gemini PRIMARY extraction complete",
            elapsed_seconds=elapsed,
            has_remuneration="remuneration" in data,
            has_allowances="allowances" in data,
            model=self._model_name,
        )

        return data
