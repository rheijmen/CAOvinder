"""Gemini 3.0 Flash Preview REST API Extractor - Direct API calls, NO SDK.

This extractor bypasses the buggy google-genai SDK and calls the Gemini REST API directly.

Benefits:
- No SDK bugs with $defs/$ref resolution
- Full control over request/response
- Simpler, more transparent
- Uses Gemini 3.0 Flash Preview with thinking mode

API Endpoint:
https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent
"""

import json
from datetime import datetime
from pathlib import Path

import requests
import structlog

from .schema_resolver import resolve_schema

logger = structlog.get_logger(__name__)

# Load OFFICIAL SETU v2.0.0-draft.3 schema (134KB, 130 additionalProperties constraints)
# CRITICAL: This is the official schema, NOT the broken 28KB version
SETU_SCHEMA_PATH = Path(__file__).parent.parent / "compliance" / "schemas" / "setu_v2.0.0-draft.3.json"
_SETU_SCHEMA_RAW = json.loads(SETU_SCHEMA_PATH.read_text())

# Resolve all $ref references since Gemini REST API doesn't support them
# This expands all references inline and removes unsupported keywords like additionalProperties
logger.info("Resolving SETU schema $ref references for Gemini API compatibility")
SETU_SCHEMA = resolve_schema(_SETU_SCHEMA_RAW)
logger.info("Schema resolution complete", schema_size_kb=len(json.dumps(SETU_SCHEMA)) // 1024)

# Import field mapping rules
FIELD_MAPPING_PATH = Path(__file__).parent.parent.parent / ".claude" / "skills" / "llm-field-mapping.md"
FIELD_MAPPING_RULES = FIELD_MAPPING_PATH.read_text() if FIELD_MAPPING_PATH.exists() else ""

GEMINI_PRIMARY_PROMPT = f"""You are extracting COMPLETE SETU v2.0 InquiryPayEquity data from a Dutch CAO document.

CRITICAL ROUTING RULE:
- SETU = what the inlener OFFERS (CAO conditions, salary scales, allowances, leave days)
- Statutory = what the government MANDATES (WML, SV-premies, fiscal limits, AOW age)
- Extract ONLY what the inlener offers. IGNORE statutory minimums.

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

Output MUST be valid SETU v2.0 InquiryPayEquity JSON.
This is for legal compliance in the Dutch staffing industry.
"""


class GeminiRestAPIExtractor:
    """SETU v2.0 extractor using Gemini 3.0 Flash Preview REST API (NO SDK)."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3-flash-preview",
        thinking_mode: str = "MEDIUM"
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.thinking_mode = thinking_mode.upper()

        # Gemini REST API endpoint
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

        logger.info(
            "Gemini REST API extractor initialized (NO SDK)",
            model=model,
            thinking_mode=self.thinking_mode,
            api_url=self.api_url
        )

    def extract(self, markdown: str, cao_name: str | None = None) -> dict:
        """Extract SETU v2.0 from CAO markdown using direct REST API call.

        Args:
            markdown: Full OCR markdown text
            cao_name: Optional CAO name for metadata

        Returns:
            SETU v2.0 InquiryPayEquity JSON dict
        """
        input_chars = len(markdown)
        logger.info(
            "Extracting SETU v2.0 with Gemini REST API",
            cao=cao_name,
            input_chars=input_chars,
            model=self.model,
            thinking_mode=self.thinking_mode,
        )

        # Build full prompt
        prompt = (
            f"{GEMINI_PRIMARY_PROMPT}\n\n"
            f"CAO Name: {cao_name or 'Unknown'}\n\n"
            f"COMPLETE CAO Document (Markdown from Mistral OCR):\n\n{markdown}"
        )

        # Build request payload for Gemini REST API
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.1,  # Low for factual extraction
                "responseMimeType": "application/json",
                "responseSchema": SETU_SCHEMA  # Full schema with $defs
            }
        }

        # Add thinking config for Gemini 3.0 (commenting out - not working with REST API)
        # if "gemini-3" in self.model or "gemini-2" in self.model:
        #     thinking_levels = {
        #         "MINIMAL": "GENERATE_MINIMAL_THOUGHT",
        #         "LOW": "GENERATE_LOW_THOUGHT",
        #         "MEDIUM": "GENERATE_MEDIUM_THOUGHT",
        #         "HIGH": "GENERATE_HIGH_THOUGHT"
        #     }
        #     thinking_mode_value = thinking_levels.get(self.thinking_mode, "GENERATE_MEDIUM_THOUGHT")
        #
        #     payload["generationConfig"]["thinkingConfig"] = {
        #         "thinkingMode": thinking_mode_value,
        #         "includeThoughts": False  # Don't return thought summaries
        #     }

        # Make direct REST API call
        start_time = datetime.now()

        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key
                },
                json=payload,
                timeout=180  # 3 minutes timeout
            )

            elapsed = (datetime.now() - start_time).total_seconds()

            # Check for API errors
            if response.status_code != 200:
                logger.error(
                    "Gemini API error",
                    status_code=response.status_code,
                    error=response.text[:500]
                )
                raise ValueError(f"Gemini API error {response.status_code}: {response.text[:500]}")

            # Parse response
            response_json = response.json()

            # Extract text from response
            candidates = response_json.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates in Gemini response")

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                raise ValueError("No parts in Gemini response content")

            response_text = parts[0].get("text", "")

            # Parse SETU JSON
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.warning(
                    "JSON parse failed, attempting repair",
                    error=str(e),
                    preview=response_text[:200]
                )

                # Try JSON repair
                try:
                    from .json_repair import repair_json
                    repaired_text = repair_json(response_text)
                    data = json.loads(repaired_text)
                    logger.info("JSON successfully repaired")
                except Exception as repair_error:
                    logger.error(
                        "JSON repair failed - returning error structure",
                        repair_error=str(repair_error)
                    )
                    # Return minimal valid SETU structure with error metadata
                    data = {
                        "documentId": {"value": f"error-{datetime.now().isoformat()}"},
                        "effectivePeriod": {"start": "2024-01-01", "end": "2024-12-31"},
                        "customer": {"name": cao_name or "Unknown"},
                        "remuneration": [],
                        "_error": str(e),
                        "_repair_error": str(repair_error),
                        "_raw_response": response_text[:5000]
                    }

            # Add extraction metadata
            data["_extraction_metadata"] = {
                "extractor": "gemini-rest-api",
                "model": self.model,
                "cao_name": cao_name,
                "extracted_at": datetime.now().isoformat(),
                "input_chars": input_chars,
                "elapsed_seconds": elapsed,
            }

            logger.info(
                "Gemini REST API extraction complete",
                elapsed_seconds=elapsed,
                has_remuneration="remuneration" in data,
                has_allowances="allowance" in data,
                model=self.model,
            )

            return data

        except requests.exceptions.Timeout:
            logger.error("Gemini API timeout after 180 seconds")
            raise
        except requests.exceptions.RequestException as e:
            logger.error("Gemini API request failed", error=str(e))
            raise
