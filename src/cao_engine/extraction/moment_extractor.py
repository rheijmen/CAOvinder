"""Dedicated moment extraction from CAO documents.

Scans OCR text for all date-driven rules, triggers, and events.
Outputs a list of Moment objects with original CAO text preserved.
The output serves as ground truth for the notification engine.
"""

import json

import structlog
from mistralai import Mistral

from cao_engine.config import Settings
from cao_engine.models.momenten import Moment, MomentenSet

from .prompts import MOMENTEN_PROMPT

logger = structlog.get_logger(__name__)

# Process in chunks to handle large CAOs
CHUNK_SIZE = 50_000  # chars per chunk
CHUNK_OVERLAP = 2_000  # overlap between chunks to avoid splitting moments


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks for processing."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


class MomentExtractor:
    """Extracts all moments from CAO OCR markdown text."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = Mistral(api_key=settings.mistral_api_key)
        self._model = settings.extraction_model

    def extract_moments(self, markdown_text: str, cao_naam: str) -> MomentenSet:
        """Extract all moments from a CAO document.

        For large documents, processes in chunks and deduplicates results.
        Each moment preserves the original CAO rule text (bron_tekst).
        """
        logger.info("Extracting moments", cao=cao_naam, text_length=len(markdown_text))

        chunks = _chunk_text(markdown_text)
        all_moments: list[Moment] = []

        for i, chunk in enumerate(chunks):
            logger.info("Processing chunk", chunk=i + 1, total=len(chunks))
            chunk_moments = self._extract_from_chunk(chunk, cao_naam, chunk_index=i)
            all_moments.extend(chunk_moments)

        # Deduplicate moments with same type + datum + bron_artikel
        deduped = self._deduplicate(all_moments)

        logger.info(
            "Moment extraction complete",
            cao=cao_naam,
            raw_count=len(all_moments),
            deduped_count=len(deduped),
        )

        return MomentenSet(
            cao_naam=cao_naam,
            momenten=deduped,
        )

    def _extract_from_chunk(
        self, text: str, cao_naam: str, chunk_index: int
    ) -> list[Moment]:
        """Extract moments from a single text chunk."""
        schema = Moment.model_json_schema()

        response = self._client.chat.complete(
            model=self._model,
            messages=[
                {"role": "system", "content": MOMENTEN_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"CAO: {cao_naam}\n\n"
                        f"JSON Schema voor elk moment:\n"
                        f"```json\n{json.dumps(schema, indent=2)}\n```\n\n"
                        f"Geef je antwoord als JSON object met een "
                        f"'momenten' array.\n\n"
                        f"CAO tekst (deel {chunk_index + 1}):\n\n{text}"
                    ),
                },
            ],
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        moments = []
        raw_moments = data.get("momenten", [])
        for raw in raw_moments:
            raw["cao_naam"] = cao_naam
            try:
                moment = Moment.model_validate(raw)
                moments.append(moment)
            except Exception as e:
                logger.warning(
                    "Failed to parse moment",
                    error=str(e),
                    raw_data=str(raw)[:200],
                )

        return moments

    def _deduplicate(self, moments: list[Moment]) -> list[Moment]:
        """Remove duplicate moments based on type + datum + bron_artikel."""
        seen: set[str] = set()
        unique: list[Moment] = []

        for m in moments:
            key = f"{m.type}|{m.datum}|{m.bron_artikel}|{m.beschrijving[:50]}"
            if key not in seen:
                seen.add(key)
                unique.append(m)

        return unique
