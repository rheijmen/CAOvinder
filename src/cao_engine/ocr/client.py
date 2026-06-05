"""Mistral OCR API client wrapper."""

import base64
from pathlib import Path

import structlog
from mistralai import Mistral

from cao_engine.config import Settings
from cao_engine.ocr.models import OCRPage, OCRPageDimensions, OCRResult, OCRTable, OCRUsageInfo

logger = structlog.get_logger(__name__)


class MistralOCRClient:
    """Wrapper around the Mistral OCR API for CAO PDF processing."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = Mistral(api_key=settings.mistral_api_key)

    def process_pdf_file(self, pdf_path: Path) -> OCRResult:
        """Process a local PDF file through Mistral OCR.

        Encodes the PDF as base64 and sends it via the document_url field.
        Uses HTML table format for accurate loontabel extraction.
        """
        size_mb = f"{pdf_path.stat().st_size / 1e6:.1f}"
        logger.info("Processing PDF", path=str(pdf_path), size_mb=size_mb)

        pdf_base64 = base64.standard_b64encode(pdf_path.read_bytes()).decode("utf-8")

        response = self._client.ocr.process(
            model=self._settings.ocr_model,
            document={
                "type": "document_url",
                "document_url": f"data:application/pdf;base64,{pdf_base64}",
            },
            table_format=self._settings.table_format,
            extract_header=self._settings.extract_headers,
            extract_footer=self._settings.extract_footers,
            include_image_base64=self._settings.include_image_base64,
        )

        pages = []
        for page in response.pages:
            dims = None
            if page.dimensions:
                dims = OCRPageDimensions(
                    dpi=page.dimensions.dpi,
                    height=page.dimensions.height,
                    width=page.dimensions.width,
                )

            # Extract tables from the page
            tables = []
            if hasattr(page, 'tables') and page.tables:
                for table in page.tables:
                    tables.append(
                        OCRTable(
                            id=table.id,
                            content=table.content,
                            format=getattr(table, 'format_', 'markdown')
                        )
                    )

            pages.append(
                OCRPage(
                    index=page.index,
                    markdown=page.markdown,
                    dimensions=dims,
                    header=getattr(page, "header", None),
                    footer=getattr(page, "footer", None),
                    tables=tables,
                )
            )

        result = OCRResult(
            model=response.model,
            pages=pages,
            usage_info=OCRUsageInfo(
                pages_processed=response.usage_info.pages_processed,
                doc_size_bytes=getattr(response.usage_info, "doc_size_bytes", None),
            ),
            document_annotation=(
                str(response.document_annotation) if response.document_annotation else None
            ),
            source_file=str(pdf_path),
        )

        logger.info(
            "OCR complete",
            pages=result.total_pages,
            model=result.model,
        )
        return result

    def process_pdf_url(self, url: str) -> OCRResult:
        """Process a PDF from a URL through Mistral OCR."""
        logger.info("Processing PDF from URL", url=url)

        response = self._client.ocr.process(
            model=self._settings.ocr_model,
            document={
                "type": "document_url",
                "document_url": url,
            },
            table_format=self._settings.table_format,
            extract_header=self._settings.extract_headers,
            extract_footer=self._settings.extract_footers,
            include_image_base64=self._settings.include_image_base64,
        )

        pages = []
        for page in response.pages:
            dims = None
            if page.dimensions:
                dims = OCRPageDimensions(
                    dpi=page.dimensions.dpi,
                    height=page.dimensions.height,
                    width=page.dimensions.width,
                )

            # Extract tables from the page
            tables = []
            if hasattr(page, 'tables') and page.tables:
                for table in page.tables:
                    tables.append(
                        OCRTable(
                            id=table.id,
                            content=table.content,
                            format=getattr(table, 'format_', 'markdown')
                        )
                    )

            pages.append(
                OCRPage(
                    index=page.index,
                    markdown=page.markdown,
                    dimensions=dims,
                    header=getattr(page, "header", None),
                    footer=getattr(page, "footer", None),
                    tables=tables,
                )
            )

        return OCRResult(
            model=response.model,
            pages=pages,
            usage_info=OCRUsageInfo(
                pages_processed=response.usage_info.pages_processed,
                doc_size_bytes=getattr(response.usage_info, "doc_size_bytes", None),
            ),
            document_annotation=(
                str(response.document_annotation) if response.document_annotation else None
            ),
            source_file=url,
        )
