"""OCR processor for single and batch CAO PDF processing."""

from pathlib import Path

import structlog

from cao_engine.config import Settings
from cao_engine.ocr.client import MistralOCRClient
from cao_engine.ocr.models import OCRResult

logger = structlog.get_logger(__name__)


class OCRProcessor:
    """Processes CAO PDFs through OCR and stores results."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = MistralOCRClient(settings)
        self._ocr_dir = settings.ocr_dir
        self._ocr_dir.mkdir(parents=True, exist_ok=True)

    def process_single(self, pdf_path: Path) -> OCRResult:
        """Process a single PDF and save OCR output.

        Saves two files:
        - {stem}.md: Combined markdown from all pages
        - {stem}.ocr.json: Full OCR result with metadata
        """
        result = self._client.process_pdf_file(pdf_path)

        # Save combined markdown
        md_path = self._ocr_dir / f"{pdf_path.stem}.md"
        md_path.write_text(result.full_markdown, encoding="utf-8")

        # Save full OCR result as JSON
        json_path = self._ocr_dir / f"{pdf_path.stem}.ocr.json"
        json_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

        logger.info(
            "Saved OCR output",
            markdown=str(md_path),
            json=str(json_path),
            pages=result.total_pages,
        )
        return result

    def process_batch(self, directory: Path) -> list[tuple[Path, OCRResult | None, str | None]]:
        """Process all PDFs in a directory.

        Returns list of (pdf_path, result_or_none, error_or_none).
        """
        pdf_files = sorted(directory.glob("*.pdf"))
        if not pdf_files:
            logger.warning("No PDF files found", directory=str(directory))
            return []

        logger.info("Starting batch processing", count=len(pdf_files), directory=str(directory))

        results: list[tuple[Path, OCRResult | None, str | None]] = []
        for pdf_path in pdf_files:
            try:
                result = self.process_single(pdf_path)
                results.append((pdf_path, result, None))
            except Exception as e:
                logger.error("Failed to process PDF", file=pdf_path.name, error=str(e))
                results.append((pdf_path, None, str(e)))

        succeeded = sum(1 for _, r, _ in results if r is not None)
        failed = sum(1 for _, _, e in results if e is not None)
        logger.info("Batch processing complete", succeeded=succeeded, failed=failed)

        return results
