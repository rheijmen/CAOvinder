"""Gemini 2.5 Flash SETU v2.0 Extractor - Fast, cheap, huge context window.

Gemini 2.5 Flash features:
- 1M token context window
- Super fast (Flash = optimized for speed)
- Very cheap (~$0.075 per 1M input tokens)
- Native JSON Schema support
- Good at structured extraction
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

GEMINI_SETU_PROMPT = """You are an expert in Dutch CAO (Collective Labour Agreement) documents and SETU v2.0 standards for the staffing industry.

Extract ONLY the employment conditions OFFERED BY THE INLENER (hiring company) from this CAO and structure according to SETU Inquiry Pay Equity v2.0 schema.

CRITICAL ROUTING RULE - Store separately, compare at read time, NEVER merge:
- SETU = what the inlener OFFERS (CAO conditions, salary scales, allowances, leave days)
- Statutory = what the government MANDATES (WML, SV-premies, fiscal limits, AOW age)
- Extract ONLY what the inlener offers. IGNORE statutory minimum wages, social insurance premiums, fiscal exemptions.

DISAMBIGUATION RULES:
1. "Pensioenregeling met 4% werkgeversbijdrage" → SETU pension
   "StiPP basis premie 12%" → IGNORE (statutory)
2. "Reiskostenvergoeding €0.23/km" → SETU allowance
   "Onbelaste reiskosten max €0.23" → IGNORE (statutory fiscal limit)
3. Salary scale with "minimumloon" flag → salaryStep.minimumWage = true
   The WML amount itself → IGNORE (statutory minimumWage)
4. "CAO-verhoging 3% per 1-7-2026" → SETU generalSalaryIncrease
   "WML stijgt naar €14.06" → IGNORE (statutory)
5. "Generatiepact" / "80-90-100" → supplementaryArrangement (NOT otherArrangement)
6. "ADV" / "ATV" / "roostervrije dagen" → leave.adv (NOT paidLeave)
7. "Feestdagen" → leave.holidays (NOT leave.paidLeave)

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

Be thorough. This is for legal compliance in the Dutch staffing industry.
"""


class GeminiSETUExtractor:
    """Extract SETU v2.0 using Gemini 2.5 Flash with 1M context."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash-preview-0924") -> None:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self._model = genai.GenerativeModel(
                model_name=model,
                generation_config={
                    "temperature": 0.1,  # Low for factual extraction
                    "response_mime_type": "application/json",
                    # Note: Not using response_schema due to compatibility issues with complex schemas
                },
            )
            self._model_name = model
            logger.info("Gemini 2.5 Flash extractor initialized", model=model)
        except ImportError:
            logger.error("google-generativeai package not installed - run: pip install google-generativeai")
            raise

    def extract(self, markdown: str, cao_name: str | None = None) -> dict:
        """Extract SETU v2.0 from full CAO using Gemini 2.5 Flash.

        Sends ENTIRE CAO (up to 1M tokens) in one call.
        Returns complete SETU v2.0 JSON.
        """
        logger.info(
            "Extracting SETU v2.0 with Gemini 2.5 Flash",
            model=self._model_name,
            cao=cao_name,
            input_chars=len(markdown),
        )
        start = datetime.utcnow()

        # Gemini 2.5 Flash has 1M token context (~4M chars)
        # Send the ENTIRE CAO!
        text = markdown  # No truncation!

        prompt = (
            f"{GEMINI_SETU_PROMPT}\n\n"
            f"SETU v2.0 Schema (follow this structure exactly):\n```json\n{json.dumps(SETU_SCHEMA, indent=2)}\n```\n\n"
            f"CAO Name: {cao_name or 'Unknown'}\n\n"
            f"COMPLETE CAO Document (Markdown from Mistral OCR):\n\n{text}"
        )

        response = self._model.generate_content(prompt)

        # Gemini returns JSON when response_mime_type is set to application/json
        data = json.loads(response.text)

        elapsed = (datetime.utcnow() - start).total_seconds()
        logger.info(
            "Gemini extraction complete",
            model=self._model_name,
            elapsed_seconds=elapsed,
            has_remuneration=bool(data.get("remuneration")),
        )

        return data
