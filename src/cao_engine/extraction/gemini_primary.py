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

# Load OFFICIAL SETU v2.0.0-rc.1 schema (Release Candidate 1, released March 11, 2026)
# CRITICAL: This is the official schema, NOT the draft.3 version
SETU_SCHEMA_PATH = Path(__file__).parent.parent / "compliance" / "schemas" / "setu_v2.0.0-rc.1.json"
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

CRITICAL: DO NOT CREATE CUSTOM FIELDS! Use existing SETU v2.0 fields.

=== CAO → SETU FIELD MAPPINGS (MUST FOLLOW EXACTLY) ===

1. ALGEMENE LOONSVERHOGING (General Salary Increase)
   Dutch aliases: "algemene loonsverhoging", "loonsverhoging", "cao-verhoging", "salarisverhogingsafspraak", "periodicale verhoging"
   English aliases: "general salary increase", "wage increase", "salary raise", "periodic increase"

   ❌ WRONG: "additionalRemunerations", "salaryAdjustments" (custom fields - NOT in SETU!)
   ✅ CORRECT: remuneration[].generalSalaryIncrease[]

   Structure:
   {{
     "remuneration": [{{
       "generalSalaryIncrease": [
         {{
           "effectivePeriod": {{"validFrom": "2024-06-01"}},
           "percentage": 2.75,
           "minimumAmount": {{"value": 74.43, "currency": "EUR"}}
         }}
       ]
     }}]
   }}

   Example: Metalektro CAO has 3 scheduled increases (June 2024, Jan 2025, June 2025)

2. EENMALIGE UITKERING (One-Time Payment / Bonus)
   Dutch aliases: "eenmalige uitkering", "bonus", "gratificatie", "afbouw eenmalige uitkering", "bijzondere uitkering", "incidentele betaling", "tijdelijke uitkering"
   English aliases: "one-time payment", "bonus", "special payment", "temporary payment", "phase-out payment"

   ❌ WRONG: "additionalRemunerations" (custom field - NOT in SETU!)
   ✅ CORRECT: supplementaryArrangement[]

   Structure:
   {{
     "supplementaryArrangement": [{{
       "name": "Afbouw eenmalige uitkering",
       "typeCode": "OneTimePayment",
       "effectivePeriod": {{
         "validFrom": "2024-06-01",
         "validTo": "2024-08-31"
       }},
       "line": [{{
         "amount": {{"value": 60, "unitCode": "Euro"}},
         "interval": {{"value": 1, "unitCode": "Month"}}
       }}]
     }}]
   }}

   Example: Metalektro "afbouw eenmalige uitkering" €60/month for 3 months

3. TOESLAGEN (Allowances)
   Dutch aliases: "toeslag", "ploegentoeslag", "overwerktoeslag", "ORT", "onregelmatigheidstoeslag", "shifttoeslag", "inconveniëntentoeslag"
   English aliases: "allowance", "shift allowance", "overtime allowance", "irregular hours allowance"

   ✅ CORRECT: allowance[]

   Structure:
   {{
     "allowance": [{{
       "name": "Overwerktoeslag",
       "typeCode": "Overtime",
       "calculationMethod": "Percentage",
       "percentage": 25.0,
       "conditions": "Na 40 uur per week"
     }}]
   }}

4. VAKANTIEGELD (Holiday Allowance)
   Dutch aliases: "vakantiegeld", "vakantie-uitkering", "vakantiebijslag"
   English aliases: "holiday allowance", "vacation pay"

   ✅ CORRECT: holidayAllowance

   Structure:
   {{
     "holidayAllowance": {{
       "percentage": 8.0,
       "payDate": "05"
     }}
   }}

5. IKB (Individual Choice Budget)
   Dutch aliases: "IKB", "individueel keuzebudget", "keuzeb udget", "flexbudget"
   English aliases: "individual choice budget", "flexible benefits budget"

   ✅ CORRECT: individualChoiceBudget

   Structure:
   {{
     "individualChoiceBudget": {{
       "amount": {{"value": 500, "currency": "EUR"}},
       "interval": {{"value": 1, "unitCode": "Year"}}
     }}
   }}

6. INDIVIDUAL STEP INCREASE (Trede verhoging)
   Dutch aliases: "periodiek", "trede verhoging", "salarisschaal stap", "individuele verhoging"
   English aliases: "individual salary increase", "step increase", "periodic step"

   ✅ CORRECT: remuneration[].individualSalaryIncrease[]

   Structure:
   {{
     "remuneration": [{{
       "individualSalaryIncrease": [{{
         "effectivePeriod": {{"validFrom": "2024-01-01"}},
         "percentage": 2.5
       }}]
     }}]
   }}

7. OTHER ARRANGEMENTS (Catch-all for rare cases)
   ✅ CORRECT: otherArrangement[]

   Use ONLY if no other field fits. Most CAO concepts fit into fields 1-8 above.

8. PENSION ARRANGEMENTS (PensionArrangement) 🔴 CRITICAL - COMMON MISTAKE!
   Dutch aliases: "pensioenregeling", "pensioenfonds", "pensioen premie", "werkgeversbijdrage pensioen", "werknemersbijdrage"
   English aliases: "pension scheme", "pension fund", "pension contribution", "employer contribution", "employee contribution"

   ✅ CORRECT: pension[]

   REQUIRED FIELDS (SETU v2.0.0-rc.1):
   - name (string): Name or description of pension fund or arrangement
   - origin (LabourAgreementReference): MUST be {{"type": "CollectiveLabourAgreement"}}

   OPTIONAL BUT RECOMMENDED:
   - line[] (array): Contribution details (employer/employee percentages, amounts)
   - franchise (object): Franchise amount/description
   - effectivePeriod (object): Period when pension applies
   - description (string): Additional details about pension scheme

   Structure (CORRECT v2.0 format):
   {{
     "pension": [{{
       "name": "Pensioenfonds Zorg en Welzijn (PfZW)",
       "origin": {{"type": "CollectiveLabourAgreement"}},
       "effectivePeriod": {{
         "validFrom": "2023-01-01",
         "validTo": "2023-12-31"
       }},
       "line": [
         {{
           "lineId": {{"value": "EMPLOYER_CONTRIBUTION"}},
           "amount": {{
             "value": 21.5,
             "unitCode": "Percentage",
             "baseAmount": {{"unitCode": "MonthlyRate", "baseType": "PensionableIncome"}}
           }},
           "interval": {{"value": 1, "unitCode": "Month"}},
           "conditions": [{{"conditionType": "Text", "description": "Werkgeversbijdrage 21,5% van pensioengrondslag"}}]
         }},
         {{
           "lineId": {{"value": "EMPLOYEE_CONTRIBUTION"}},
           "amount": {{
             "value": 5.5,
             "unitCode": "Percentage",
             "baseAmount": {{"unitCode": "MonthlyRate", "baseType": "PensionableIncome"}}
           }},
           "interval": {{"value": 1, "unitCode": "Month"}},
           "conditions": [{{"conditionType": "Text", "description": "Werknemersbijdrage 5,5% van pensioengrondslag (standaard)"}}]
         }}
       ],
       "franchise": {{
         "description": "Franchise € 17.545 (2024), jaarlijks aangepast conform wettelijk minimum"
       }},
       "description": "Pensioenregeling uitgevoerd door Pensioenfonds Zorg en Welzijn. Premieverdeling 60/40 werkgever/werknemer."
     }}]
   }}

   ❌ WRONG - DO NOT CREATE THESE FIELDS (they are NOT in SETU v2.0 schema):
   - pensionFundName (use "name" instead!)
   - employerContribution (use line[] instead!)
   - employeeContribution (use line[] instead!)
   - pensionScheme (use "description" instead!)
   - pensionAge (not part of PensionArrangement)
   - pensionSchemeType (not part of PensionArrangement)

   VALIDATION CHECKLIST:
   ✅ Field "name" exists and contains pension fund/arrangement name
   ✅ Field "origin" exists with {{"type": "CollectiveLabourAgreement"}}
   ✅ Contributions are in line[] array (NOT as separate objects)
   ✅ Each line[] item has REQUIRED "interval" field: {{"value": 1, "unitCode": "Month"}}
   ✅ Each line[] item amount has REQUIRED "baseAmount" field: {{"unitCode": "MonthlyRate", "baseType": "PensionableIncome"}}
   ✅ NO custom fields like pensionFundName, employerContribution, employeeContribution

   REAL EXAMPLE (from Rabobank CAO - VALID ✅):
   {{
     "pension": [{{
       "name": "Rabobank Pensioenfonds - Collectieve pensioenregeling",
       "origin": {{"type": "CollectiveLabourAgreement"}},
       "effectivePeriod": {{"validFrom": "2024-07-01", "validTo": "2025-06-30"}},
       "line": [
         {{
           "lineId": {{"value": "PENSION_PREMIE"}},
           "amount": {{"value": 27, "unitCode": "Percentage", "baseAmount": {{"unitCode": "MonthlyRate", "baseType": "Pensioengrondslag"}}}},
           "interval": {{"value": 1, "unitCode": "Month"}}
         }},
         {{
           "lineId": {{"value": "PENSION_PARTNER_RISICO"}},
           "amount": {{"value": 1.313, "unitCode": "Percentage", "baseAmount": {{"unitCode": "YearlyRate", "baseType": "PensioengevendJaarinkomen"}}}},
           "interval": {{"value": 1, "unitCode": "Year"}}
         }},
         {{
           "lineId": {{"value": "PENSION_WEZEN_RISICO"}},
           "amount": {{"value": 0.263, "unitCode": "Percentage", "baseAmount": {{"unitCode": "YearlyRate", "baseType": "PensioengevendJaarinkomen"}}}},
           "interval": {{"value": 1, "unitCode": "Year"}}
         }}
       ],
       "franchise": {{"description": "Franchise € 17.545 (2024), jaarlijks aangepast"}},
       "description": "Pensioenrichtleeftijd 68 jaar. Flexibilisering mogelijk. Werkgeversbijdrage 21,5%, werknemersbijdrage 5,5%."
     }}]
   }}

=== DECISION LOGIC ===

When you see:
- "Algemene loonsverhoging 2.75% per 1 juni 2024" → generalSalaryIncrease
- "Eenmalige uitkering €60 per maand" → supplementaryArrangement
- "Ploegentoeslag 25%" → allowance
- "Vakantiegeld 8%" → holidayAllowance
- "IKB €500 per jaar" → individualChoiceBudget
- "Periodieken jaarlijks 2.5%" → individualSalaryIncrease
- "Pensioenfonds Zorg en Welzijn, werkgever 60%, werknemer 40%" → pension[] with name + origin + line[]

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

Output MUST be valid SETU v2.0 InquiryPayEquity JSON - NO CUSTOM FIELDS!

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
