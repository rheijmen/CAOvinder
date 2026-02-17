"""Claude Opus 4.6 SETU v2.0 Extractor - Uses 1M context window for full CAO processing.

This is likely the BEST approach because:
1. 1M token context = entire CAO fits
2. Best reasoning for complex structured extraction
3. 128k output tokens = can generate massive SETU JSON
4. One API call = fast and simple
"""

import json
from datetime import datetime
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

# Load SETU v2.0 schema
SETU_SCHEMA_PATH = Path(__file__).parent.parent / "models" / "setu_v2_schema.json"
SETU_SCHEMA = json.loads(SETU_SCHEMA_PATH.read_text())

CLAUDE_SETU_PROMPT = """Je bent een expert in Nederlandse CAO's en SETU v2.0 standaarden voor de uitzendbranche.

Je taak is om deze COMPLETE CAO te analyseren en ALLE arbeidsvoorwaarden en remuneratie te structureren volgens het SETU Inquiry Pay Equity v2.0 schema.

CRITICAL REQUIREMENTS:
1. Extract EVERY functiegroep, schaal, and trede from salary tables
2. Find ALL toeslagen (ORT, ploegentoeslag, overwerk, etc.) with exact percentages
3. Identify vakantietoeslag percentage and payment month
4. Map ADV/arbeidsduurverkorting to the leave element
5. Extract pension schemes and franchises
6. Use EXACT terminology from the CAO
7. For unknown fields use null (not empty string)

The output MUST be valid SETU v2.0 InquiryPayEquity JSON.

Take your time. Be thorough. This is important for legal compliance.
"""


class ClaudeOpusSETUExtractor:
    """Extract SETU v2.0 using Claude Opus 4.6's 1M context window."""

    def __init__(self, api_key: str, model: str = "claude-opus-4.6-20260205") -> None:
        try:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=api_key)
            self._model = model
            logger.info("Claude Opus 4.6 extractor initialized", model=model)
        except ImportError:
            logger.error("anthropic package not installed - run: pip install anthropic")
            raise

    def extract(self, markdown: str, cao_name: str | None = None) -> dict:
        """Extract SETU v2.0 from full CAO using Claude Opus 4.6.

        Sends ENTIRE CAO (up to 1M tokens) in one call.
        Returns complete SETU v2.0 JSON.
        """
        logger.info(
            "Extracting SETU v2.0 with Claude Opus 4.6",
            model=self._model,
            cao=cao_name,
            input_chars=len(markdown),
        )
        start = datetime.utcnow()

        # Claude Opus 4.6 has 1M token context (~4M chars)
        # We can send the ENTIRE CAO!
        text = markdown  # No truncation needed!

        response = self._client.messages.create(
            model=self._model,
            max_tokens=128000,  # Use full 128k output capacity
            temperature=0.1,  # Low for factual extraction
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"{CLAUDE_SETU_PROMPT}\n\n"
                        f"CAO Naam: {cao_name or 'Onbekend'}\n\n"
                        f"SETU v2.0 JSON Schema:\n```json\n{json.dumps(SETU_SCHEMA, indent=2)}\n```\n\n"
                        f"COMPLETE CAO Document (Markdown from Mistral OCR):\n\n{text}"
                    ),
                }
            ],
            # Use new output_config format for Opus 4.6
            # Note: output_format is deprecated, use output_config
            # But for now, let's try JSON mode first
        )

        content = response.content[0].text

        # Extract JSON from markdown code blocks if needed
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        data = json.loads(content)

        elapsed = (datetime.utcnow() - start).total_seconds()
        logger.info(
            "Claude extraction complete",
            model=self._model,
            elapsed_seconds=elapsed,
            has_remuneration=bool(data.get("remuneration")),
            output_tokens=response.usage.output_tokens,
            input_tokens=response.usage.input_tokens,
        )

        return data
