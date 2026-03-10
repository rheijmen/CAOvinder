"""Gemini 3 Flash Preview Primary SETU Extractor - First pass extraction.

This is the PRIMARY extractor in the 3-LLM sequential pipeline:
1. Gemini 3 Flash Preview (this) - Extract SETU v2.0 completely with thinking mode
2. Mistral Large - Review & find gaps
3. Mistral Small - Judge which output is best

Uses Gemini 3 Flash Preview features:
- Thinking mode (MEDIUM level for cost/quality balance)
- Response schema for guaranteed valid JSON
- 1M context window for full CAO documents
"""

import json
from datetime import datetime
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

# Load OFFICIAL SETU v2.0.0-draft.3 schema (134KB, 130 additionalProperties constraints)
# CRITICAL: This is the official schema, NOT the broken 28KB version
SETU_SCHEMA_PATH = Path(__file__).parent.parent / "compliance" / "schemas" / "setu_v2.0.0-draft.3.json"
_SETU_SCHEMA_RAW = json.loads(SETU_SCHEMA_PATH.read_text())

# Strip JSON Schema Draft 2020-12 metadata fields that Gemini SDK doesn't support
# Remove: $schema, $id, title, description
# Keep: type, required, properties, AND $defs (needed for $ref resolution!)
SETU_SCHEMA = {
    "type": _SETU_SCHEMA_RAW.get("type"),
    "required": _SETU_SCHEMA_RAW.get("required"),
    "properties": _SETU_SCHEMA_RAW.get("properties"),
    "$defs": _SETU_SCHEMA_RAW.get("$defs"),  # CRITICAL: Keep for $ref resolution
}

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
    """Primary SETU v2.0 extractor using Gemini 3 Flash Preview with thinking mode (new SDK)."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3-flash-preview",
        thinking_level: str = "MEDIUM"
    ) -> None:
        try:
            # Use NEW google.genai SDK (replaces deprecated google.generativeai)
            from google import genai
            from google.genai import types

            self._client = genai.Client(api_key=api_key)
            self._model_name = model
            self._thinking_level = thinking_level.upper()

            # Build generation config with response_schema
            self._config = types.GenerateContentConfig(
                temperature=0.1,  # Low for factual extraction
                response_mime_type="application/json",
                response_schema=SETU_SCHEMA,  # Guaranteed valid JSON structure
            )

            # Add thinking_config if model supports it (Gemini 2.5/3 series)
            if "gemini-2" in model or "gemini-3" in model:
                # Map thinking level string to enum
                thinking_level_map = {
                    "MINIMAL": types.ThinkingLevel.MINIMAL,
                    "LOW": types.ThinkingLevel.LOW,
                    "MEDIUM": types.ThinkingLevel.MEDIUM,
                    "HIGH": types.ThinkingLevel.HIGH,
                }
                level_enum = thinking_level_map.get(self._thinking_level, types.ThinkingLevel.MEDIUM)

                self._config.thinking_config = types.ThinkingConfig(
                    thinking_level=level_enum,
                    include_thoughts=False  # Don't return thought summaries (save tokens)
                )
                logger.info(
                    "Gemini 3 Flash Preview PRIMARY extractor initialized (NEW SDK)",
                    model=model,
                    thinking_level=self._thinking_level,
                    response_schema_enabled=True,
                    thinking_enabled=True
                )
            else:
                logger.info(
                    "Gemini extractor initialized (NEW SDK)",
                    model=model,
                    response_schema_enabled=True,
                    thinking_enabled=False
                )
        except ImportError as e:
            raise ImportError(
                "google-genai package required. Install with: pip install google-genai"
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
            "Extracting SETU v2.0 with Gemini 3 Flash Preview (PRIMARY)",
            cao=cao_name,
            input_chars=input_chars,
            model=self._model_name,
            thinking_level=self._thinking_level,
        )

        # Build prompt with full schema and full CAO text (1M context!)
        prompt = (
            f"{GEMINI_PRIMARY_PROMPT}\n\n"
            f"SETU v2.0 Schema (follow this structure exactly):\n```json\n{json.dumps(SETU_SCHEMA, indent=2)}\n```\n\n"
            f"CAO Name: {cao_name or 'Unknown'}\n\n"
            f"COMPLETE CAO Document (Markdown from Mistral OCR):\n\n{markdown}"
        )

        start_time = datetime.now()
        # Use NEW SDK API: client.models.generate_content()
        response = self._client.models.generate_content(
            model=self._model_name,
            contents=prompt,
            config=self._config
        )
        elapsed = (datetime.now() - start_time).total_seconds()

        # Gemini 3 with response_schema should ALWAYS return valid JSON
        # Extract text from new SDK response format
        try:
            response_text = response.text if hasattr(response, 'text') else str(response)
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.warning(
                "JSON parse failed despite response_schema, attempting repair",
                error=str(e),
                preview=response.text[:200]
            )

            # Try JSON repair
            try:
                from .json_repair import repair_json
                repaired_text = repair_json(response.text)
                data = json.loads(repaired_text)
                logger.info("JSON successfully repaired")
            except Exception as repair_error:
                logger.error(
                    "JSON repair failed - returning error structure",
                    repair_error=str(repair_error)
                )
                # Return minimal valid SETU structure with error metadata
                data = {
                    "documentId": f"error-{datetime.now().isoformat()}",
                    "versionCode": "1.0",
                    "creationDateTime": datetime.now().isoformat(),
                    "inlener": {"name": cao_name or "Unknown"},
                    "_error": str(e),
                    "_repair_error": str(repair_error),
                    "_raw_response": response.text[:5000]
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
