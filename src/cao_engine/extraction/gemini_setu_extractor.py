"""Gemini 2.5 Flash SETU v2.0 Extractor - Fast, cheap, huge context window.

Gemini 2.5 Flash features:
- 1M token context window
- Super fast (Flash = optimized for speed)
- Very cheap (~$0.075 per 1M input tokens)
- Native JSON Schema support
- Good at structured extraction

GOLD STANDARD: Uses SETU Compliance Engine for schema-driven extraction.
"""

import json
from datetime import datetime
from pathlib import Path

import structlog

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
_SETU_SCHEMA_RAW = json.loads(SETU_SCHEMA_PATH.read_text())

# Strip JSON Schema metadata fields that Gemini doesn't support
SETU_SCHEMA = {k: v for k, v in _SETU_SCHEMA_RAW.items() if k not in ("$schema", "$id")}


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

            # Initialize SETU Compliance Engine
            self._compliance_engine = get_compliance_engine()

            logger.info("Gemini 2.5 Flash extractor initialized with SETU Compliance Engine",
                       model=model,
                       setu_version=self._compliance_engine.current_version)
        except ImportError:
            logger.error("google-generativeai package not installed - run: pip install google-generativeai")
            raise

    def extract(self, markdown: str, cao_name: str | None = None) -> dict:
        """Extract SETU v2.0 from full CAO using Gemini 2.5 Flash.

        Sends ENTIRE CAO (up to 1M tokens) in one call.
        Returns complete SETU v2.0 JSON.

        GOLD STANDARD: Uses SETU Compliance Engine for extraction prompt.
        """
        logger.info(
            "Extracting SETU v2.0 with Gemini 2.5 Flash + Compliance Engine",
            model=self._model_name,
            cao=cao_name,
            input_chars=len(markdown),
            setu_version=self._compliance_engine.current_version,
        )
        start = datetime.utcnow()

        # Check for SETU schema updates
        update = self._compliance_engine.check_for_updates()
        if update:
            logger.warning("SETU schema update available",
                          new_version=update.version,
                          breaking_changes=update.breaking_changes)

        # Get GOLD STANDARD extraction prompt from compliance engine
        compliance_prompt = self._compliance_engine.generate_extraction_prompt()

        # Gemini 2.5 Flash has 1M token context (~4M chars)
        # Send the ENTIRE CAO!
        text = markdown  # No truncation!

        # Add schema for Gemini (it supports JSON schema natively)
        prompt = (
            f"{compliance_prompt}\n\n"
            f"SETU v2.0 Schema (follow this structure exactly):\n```json\n{json.dumps(SETU_SCHEMA, indent=2)}\n```\n\n"
            f"CAO Name: {cao_name or 'Unknown'}\n\n"
            f"COMPLETE CAO Document (Markdown from Mistral OCR):\n\n{text}"
        )

        response = self._model.generate_content(prompt)

        # Gemini returns JSON when response_mime_type is set to application/json
        data = json.loads(response.text)

        # Validate extraction against SETU schema
        status, report = self._compliance_engine.validate_extraction(data)

        elapsed = (datetime.utcnow() - start).total_seconds()
        logger.info(
            "Gemini extraction complete with compliance validation",
            model=self._model_name,
            elapsed_seconds=elapsed,
            has_remuneration=bool(data.get("remuneration")),
            compliance_status=status.value,
            coverage=report["coverage"],
            errors=len(report.get("errors", [])),
            warnings=len(report.get("warnings", [])),
        )

        # Add compliance metadata to extraction
        data["_compliance"] = {
            "status": status.value,
            "coverage": report["coverage"],
            "validated_at": datetime.now().isoformat(),
            "setu_version": self._compliance_engine.current_version,
            "errors": report.get("errors", []),
            "warnings": report.get("warnings", [])
        }

        return data
