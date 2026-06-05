"""Parallel and batch-enabled CAO extraction for speed and cost optimization.

This module provides:
1. Parallel extraction - run all 5 extractions concurrently (5x faster)
2. Batch API support - 50% cost reduction for async processing
"""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import structlog
from mistralai import Mistral

from cao_engine.config import Settings
from cao_engine.models import (
    ArbeidsVoorwaarden,
    CAOMetadata,
    InlenersbeloningElementen,
    Loongebouw,
)
from cao_engine.models.momenten import MomentenSet

from .parser import _clean_llm_output, _get_json_schema
from .prompts import (
    ARBEIDSVOORWAARDEN_PROMPT,
    CAO_METADATA_PROMPT,
    INLENERSBELONING_PROMPT,
    LOONGEBOUW_PROMPT,
    MOMENTEN_PROMPT,
)

logger = structlog.get_logger(__name__)


class ParallelCAOExtractor:
    """Extract CAO data using parallel API calls for 5x speed improvement."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = Mistral(api_key=settings.mistral_api_key)
        self._model = settings.extraction_model

    def extract_all_parallel(
        self, markdown_text: str, cao_naam: str
    ) -> tuple[CAOMetadata, Loongebouw, ArbeidsVoorwaarden, InlenersbeloningElementen, MomentenSet]:
        """Extract all CAO components in parallel using ThreadPoolExecutor.

        This runs all 5 extraction tasks concurrently, reducing total time
        from ~5 minutes to ~1 minute.
        """
        logger.info("Starting parallel extraction", cao=cao_naam)
        start = datetime.utcnow()

        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all tasks concurrently
            future_metadata = executor.submit(
                self._extract_component, markdown_text, CAO_METADATA_PROMPT, CAOMetadata
            )
            future_loongebouw = executor.submit(
                self._extract_component, markdown_text, LOONGEBOUW_PROMPT, Loongebouw
            )
            future_arbeidsvoorwaarden = executor.submit(
                self._extract_component,
                markdown_text,
                ARBEIDSVOORWAARDEN_PROMPT,
                ArbeidsVoorwaarden,
            )
            future_inlenersbeloning = executor.submit(
                self._extract_component,
                markdown_text,
                INLENERSBELONING_PROMPT,
                InlenersbeloningElementen,
            )
            future_momenten = executor.submit(
                self._extract_moments_simple, markdown_text, cao_naam
            )

            # Wait for all results
            metadata = future_metadata.result()
            loongebouw = future_loongebouw.result()
            arbeidsvoorwaarden = future_arbeidsvoorwaarden.result()
            inlenersbeloning = future_inlenersbeloning.result()
            momenten_set = future_momenten.result()

        elapsed = (datetime.utcnow() - start).total_seconds()
        logger.info("Parallel extraction complete", cao=cao_naam, elapsed_seconds=elapsed)

        return metadata, loongebouw, arbeidsvoorwaarden, inlenersbeloning, momenten_set

    def _extract_component(self, markdown_text: str, system_prompt: str, model_class: type) -> object:
        """Extract a single component using the LLM."""
        schema = _get_json_schema(model_class)
        text = markdown_text[:200_000]  # Truncate to context window

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
        cleaned = _clean_llm_output(data)

        return model_class.model_validate(cleaned)

    def _extract_moments_simple(self, markdown_text: str, cao_naam: str) -> MomentenSet:
        """Extract moments without chunking for speed.

        For documents > 200k chars, this will only process first 200k.
        Use batch API for full chunked processing.
        """
        from cao_engine.models.momenten import Moment

        text = markdown_text[:200_000]
        schema = _get_json_schema(Moment)

        response = self._client.chat.complete(
            model=self._model,
            messages=[
                {"role": "system", "content": MOMENTEN_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"CAO: {cao_naam}\n\n"
                        f"JSON Schema voor elk moment:\n```json\n{json.dumps(schema, indent=2)}\n```\n\n"
                        f"Geef je antwoord als JSON object met een 'momenten' array.\n\n"
                        f"CAO tekst:\n\n{text}"
                    ),
                },
            ],
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        moments = []
        for raw in data.get("momenten", []):
            raw["cao_naam"] = cao_naam
            try:
                cleaned = _clean_llm_output(raw)
                moment = Moment.model_validate(cleaned)
                moments.append(moment)
            except Exception as e:
                logger.warning("Failed to parse moment", error=str(e))

        return MomentenSet(cao_naam=cao_naam, momenten=moments)


class BatchCAOExtractor:
    """Extract CAO data using Mistral Batch API for 50% cost reduction.

    Batch processing is async and takes longer but costs half as much.
    Ideal for processing many CAOs overnight.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = Mistral(api_key=settings.mistral_api_key)
        self._model = settings.extraction_model

    def create_batch_extraction(self, ocr_files: list[Path]) -> str:
        """Create a batch job for extracting multiple CAO files.

        Returns batch job ID for status tracking.
        """
        # Create batch request file
        batch_requests = []
        for i, ocr_path in enumerate(ocr_files):
            markdown = ocr_path.read_text(encoding="utf-8")[:200_000]
            cao_naam = ocr_path.stem

            # Create 5 requests per CAO
            batch_requests.extend(
                [
                    self._create_batch_request(
                        f"{cao_naam}_metadata_{i}", markdown, CAO_METADATA_PROMPT
                    ),
                    self._create_batch_request(
                        f"{cao_naam}_loongebouw_{i}", markdown, LOONGEBOUW_PROMPT
                    ),
                    self._create_batch_request(
                        f"{cao_naam}_arbeidsvoorwaarden_{i}", markdown, ARBEIDSVOORWAARDEN_PROMPT
                    ),
                    self._create_batch_request(
                        f"{cao_naam}_inlenersbeloning_{i}", markdown, INLENERSBELONING_PROMPT
                    ),
                    self._create_batch_request(
                        f"{cao_naam}_momenten_{i}", markdown, MOMENTEN_PROMPT
                    ),
                ]
            )

        # Write batch file
        batch_file = self._settings.data_dir / "batch_requests.jsonl"
        with open(batch_file, "w") as f:
            for req in batch_requests:
                f.write(json.dumps(req) + "\n")

        # Upload and create batch job
        logger.info("Uploading batch file", file=str(batch_file), requests=len(batch_requests))
        uploaded = self._client.files.upload(
            file={"file_name": "batch_requests.jsonl", "content": open(batch_file, "rb")},
            purpose="batch",
        )

        logger.info("Creating batch job", file_id=uploaded.id)
        job = self._client.batch.jobs.create(
            input_files=[uploaded.id],
            model=self._model,
            endpoint="/v1/chat/completions",
        )

        logger.info("Batch job created", job_id=job.id, status=job.status)
        return job.id

    def _create_batch_request(self, custom_id: str, markdown: str, prompt: str) -> dict:
        """Create a single batch request."""
        return {
            "custom_id": custom_id,
            "body": {
                "model": self._model,
                "messages": [
                    {"role": "system", "content": prompt},
                    {
                        "role": "user",
                        "content": f"Extraheer de gevraagde data:\n\n{markdown}",
                    },
                ],
                "response_format": {"type": "json_object"},
            },
        }

    def check_batch_status(self, job_id: str) -> dict:
        """Check status of a batch job."""
        job = self._client.batch.jobs.get(job_id)
        return {
            "id": job.id,
            "status": job.status,
            "created_at": job.created_at,
            "completed_at": getattr(job, "completed_at", None),
            "total_requests": getattr(job, "total_requests", 0),
            "succeeded_requests": getattr(job, "succeeded_requests", 0),
            "failed_requests": getattr(job, "failed_requests", 0),
        }
