"""CAO data extractor using Mistral LLM with structured output."""

import json

import structlog
from mistralai import Mistral

from cao_engine.config import Settings
from cao_engine.models import (
    ArbeidsVoorwaarden,
    CAOMetadata,
    InlenersbeloningElementen,
    Loongebouw,
)

from .prompts import (
    ARBEIDSVOORWAARDEN_PROMPT,
    CAO_METADATA_PROMPT,
    INLENERSBELONING_PROMPT,
    LOONGEBOUW_PROMPT,
)

logger = structlog.get_logger(__name__)

# Maximum characters to send per extraction call
# Mistral Large has 128k context window (~512k chars)
# Using 200k chars to stay well within limits while allowing full CAO processing
MAX_CONTEXT_CHARS = 200_000


def _get_json_schema(model_class: type) -> dict:
    """Get JSON schema from a Pydantic model for structured output."""
    return model_class.model_json_schema()


def _clean_llm_output(data: dict) -> dict:
    """Recursively clean LLM output to replace None with appropriate defaults.

    This handles cases where the LLM explicitly returns null/None for fields
    that have default_factory values in Pydantic models.
    """
    if not isinstance(data, dict):
        return data

    cleaned = {}
    for key, value in data.items():
        if value is None:
            # Skip None values - let Pydantic use defaults
            continue
        elif isinstance(value, dict):
            cleaned[key] = _clean_llm_output(value)
        elif isinstance(value, list):
            cleaned[key] = [_clean_llm_output(item) if isinstance(item, dict) else item
                           for item in value]
        else:
            cleaned[key] = value
    return cleaned


class CAOExtractor:
    """Extracts structured CAO data from OCR markdown using Mistral LLM."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = Mistral(api_key=settings.mistral_api_key)
        self._model = settings.extraction_model

    def _extract_with_schema(
        self, markdown_text: str, system_prompt: str, model_class: type
    ) -> dict:
        """Generic extraction: send markdown + prompt, get structured JSON back."""
        schema = _get_json_schema(model_class)

        # Truncate if needed
        text = markdown_text[:MAX_CONTEXT_CHARS]
        if len(markdown_text) > MAX_CONTEXT_CHARS:
            logger.warning(
                "Text truncated for extraction",
                original_chars=len(markdown_text),
                truncated_to=MAX_CONTEXT_CHARS,
            )

        response = self._client.chat.complete(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Extraheer de gevraagde data uit het volgende CAO-document.\n\n"
                        f"JSON Schema:\n```json\n{json.dumps(schema, indent=2)}\n```\n\n"
                        f"CAO Document:\n\n{text}"
                    ),
                },
            ],
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        return _clean_llm_output(data)

    def extract_metadata(self, markdown_text: str) -> CAOMetadata:
        """Extract CAO metadata from OCR markdown."""
        logger.info("Extracting metadata")
        data = self._extract_with_schema(markdown_text, CAO_METADATA_PROMPT, CAOMetadata)
        return CAOMetadata.model_validate(data)

    def extract_loongebouw(self, markdown_text: str) -> Loongebouw:
        """Extract wage structure from OCR markdown."""
        logger.info("Extracting loongebouw")
        data = self._extract_with_schema(markdown_text, LOONGEBOUW_PROMPT, Loongebouw)
        return Loongebouw.model_validate(data)

    def extract_arbeidsvoorwaarden(self, markdown_text: str) -> ArbeidsVoorwaarden:
        """Extract employment conditions from OCR markdown."""
        logger.info("Extracting arbeidsvoorwaarden")
        data = self._extract_with_schema(
            markdown_text, ARBEIDSVOORWAARDEN_PROMPT, ArbeidsVoorwaarden
        )
        return ArbeidsVoorwaarden.model_validate(data)

    def extract_inlenersbeloning(self, markdown_text: str) -> InlenersbeloningElementen:
        """Extract inlenersbeloning elements from OCR markdown."""
        logger.info("Extracting inlenersbeloning")
        data = self._extract_with_schema(
            markdown_text, INLENERSBELONING_PROMPT, InlenersbeloningElementen
        )
        return InlenersbeloningElementen.model_validate(data)
