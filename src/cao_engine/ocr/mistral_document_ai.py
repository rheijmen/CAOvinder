"""
Mistral Document AI Integration for CAO Processing
==================================================
Uses Mistral's OCR API (mistral-ocr-latest) for superior document extraction.

Key advantages over basic OCR:
- Table extraction in HTML/Markdown format
- Header/footer separation
- Image bbox extraction with base64
- Hyperlink preservation
- Multi-column layout handling

Two-Tier Extraction:
1. Basic OCR - Full document extraction (all pages)
2. Document Annotation - Schema-based extraction with confidence scores (up to 8 pages)
"""

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog
from mistralai import Mistral
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


@dataclass
class TableExtraction:
    """Represents an extracted table from the document."""
    id: str
    content: str
    format: str  # "html" or "markdown"
    page_index: int


@dataclass
class ImageExtraction:
    """Represents an extracted image from the document."""
    id: str
    top_left_x: int
    top_left_y: int
    bottom_right_x: int
    bottom_right_y: int
    image_base64: str | None
    page_index: int


@dataclass
class PageExtraction:
    """Represents a single page extraction result."""
    index: int
    markdown: str
    tables: list[TableExtraction]
    images: list[ImageExtraction]
    hyperlinks: list[str]
    header: str | None
    footer: str | None
    dimensions: dict[str, int]


@dataclass
class DocumentExtractionResult:
    """Complete document extraction result."""
    pages: list[PageExtraction]
    model: str
    total_pages: int
    total_tables: int
    total_images: int
    total_hyperlinks: int


class MistralDocumentAI:
    """
    Mistral Document AI client for CAO PDF processing.

    Uses mistral-ocr-latest model with optimized settings for CAO documents:
    - HTML table extraction (critical for salary scales)
    - Header/footer separation (for document metadata)
    - Image extraction (for diagrams, org charts)
    - Hyperlink preservation (for references)
    """

    def __init__(self, api_key: str | None = None):
        """
        Initialize Mistral Document AI client.

        Args:
            api_key: Mistral API key. If None, reads from MISTRAL_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY environment variable not set")

        self.client = Mistral(api_key=self.api_key)
        self.model = "mistral-ocr-latest"

        logger.info(
            "MistralDocumentAI initialized",
            model=self.model
        )

    def process_pdf(
        self,
        pdf_path: Path,
        table_format: str = "html",
        extract_header: bool = True,
        extract_footer: bool = True,
        include_image_base64: bool = True
    ) -> DocumentExtractionResult:
        """
        Process a CAO PDF through Mistral Document AI.

        Args:
            pdf_path: Path to PDF file
            table_format: "html", "markdown", or None. Use "html" for best CAO table extraction.
            extract_header: Extract headers separately (for CAO metadata)
            extract_footer: Extract footers separately (for version info)
            include_image_base64: Include base64-encoded images

        Returns:
            DocumentExtractionResult with structured extraction data
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        logger.info(
            "Processing PDF with Mistral Document AI",
            pdf=pdf_path.name,
            size_mb=round(pdf_path.stat().st_size / 1024 / 1024, 2),
            table_format=table_format
        )

        # Encode PDF to base64
        with open(pdf_path, "rb") as f:
            pdf_base64 = base64.b64encode(f.read()).decode('utf-8')

        # Call Mistral OCR API
        response = self.client.ocr.process(
            model=self.model,
            document={
                "type": "document_url",
                "document_url": f"data:application/pdf;base64,{pdf_base64}"
            },
            table_format=table_format,
            extract_header=extract_header,
            extract_footer=extract_footer,
            include_image_base64=include_image_base64
        )

        # Parse response into structured result
        pages = []
        total_tables = 0
        total_images = 0
        total_hyperlinks = 0

        for page_data in response.pages:
            # Extract tables
            tables = []
            if page_data.tables:
                for table in page_data.tables:
                    tables.append(TableExtraction(
                        id=table.id,
                        content=table.content,
                        format=table.format_ if hasattr(table, 'format_') else 'html',
                        page_index=page_data.index
                    ))
                    total_tables += 1

            # Extract images
            images = []
            if page_data.images:
                for img in page_data.images:
                    images.append(ImageExtraction(
                        id=img.id,
                        top_left_x=img.top_left_x,
                        top_left_y=img.top_left_y,
                        bottom_right_x=img.bottom_right_x,
                        bottom_right_y=img.bottom_right_y,
                        image_base64=img.image_base64 if include_image_base64 else None,
                        page_index=page_data.index
                    ))
                    total_images += 1

            # Count hyperlinks
            hyperlinks = page_data.hyperlinks if page_data.hyperlinks else []
            total_hyperlinks += len(hyperlinks)

            # Create page extraction
            pages.append(PageExtraction(
                index=page_data.index,
                markdown=page_data.markdown,
                tables=tables,
                images=images,
                hyperlinks=hyperlinks,
                header=page_data.header,
                footer=page_data.footer,
                dimensions=page_data.dimensions
            ))

        result = DocumentExtractionResult(
            pages=pages,
            model=response.model,
            total_pages=len(pages),
            total_tables=total_tables,
            total_images=total_images,
            total_hyperlinks=total_hyperlinks
        )

        logger.info(
            "PDF processing complete",
            pages=result.total_pages,
            tables=result.total_tables,
            images=result.total_images,
            hyperlinks=result.total_hyperlinks
        )

        return result

    def save_extraction(
        self,
        result: DocumentExtractionResult,
        output_path: Path,
        include_images: bool = False
    ) -> None:
        """
        Save extraction result to JSON file.

        Args:
            result: Document extraction result
            output_path: Path to save JSON output
            include_images: Include base64 images in JSON (can be large)
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict
        output = {
            "model": result.model,
            "total_pages": result.total_pages,
            "total_tables": result.total_tables,
            "total_images": result.total_images,
            "total_hyperlinks": result.total_hyperlinks,
            "pages": []
        }

        for page in result.pages:
            # Convert dimensions object to dict
            dimensions_dict = {}
            if page.dimensions:
                if hasattr(page.dimensions, 'model_dump'):
                    dimensions_dict = page.dimensions.model_dump()
                elif hasattr(page.dimensions, 'dict'):
                    dimensions_dict = page.dimensions.dict()
                else:
                    # Manual conversion if needed
                    dimensions_dict = {
                        "width": getattr(page.dimensions, 'width', None),
                        "height": getattr(page.dimensions, 'height', None)
                    }

            page_data = {
                "index": page.index,
                "markdown": page.markdown,
                "header": page.header,
                "footer": page.footer,
                "dimensions": dimensions_dict,
                "hyperlinks": page.hyperlinks,
                "tables": [
                    {
                        "id": t.id,
                        "content": t.content,
                        "format": t.format
                    }
                    for t in page.tables
                ],
                "images": [
                    {
                        "id": img.id,
                        "bbox": {
                            "top_left": {"x": img.top_left_x, "y": img.top_left_y},
                            "bottom_right": {"x": img.bottom_right_x, "y": img.bottom_right_y}
                        },
                        "base64": img.image_base64 if include_images else None
                    }
                    for img in page.images
                ]
            }
            output["pages"].append(page_data)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        logger.info(
            "Extraction saved",
            output=output_path.name,
            size_kb=round(output_path.stat().st_size / 1024, 2)
        )

    def save_markdown(
        self,
        result: DocumentExtractionResult,
        output_path: Path
    ) -> None:
        """
        Save extraction result as markdown file.

        Combines all page markdown with table references.

        Args:
            result: Document extraction result
            output_path: Path to save markdown output
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        markdown_parts = []

        # Add metadata header
        markdown_parts.append("# CAO Document\n")
        markdown_parts.append(f"**Model:** {result.model}\n")
        markdown_parts.append(f"**Pages:** {result.total_pages}\n")
        markdown_parts.append(f"**Tables:** {result.total_tables}\n")
        markdown_parts.append(f"**Images:** {result.total_images}\n")
        markdown_parts.append("\n---\n\n")

        # Add each page
        for page in result.pages:
            markdown_parts.append(f"## Page {page.index + 1}\n\n")

            # Add header if present
            if page.header:
                markdown_parts.append(f"**Header:** {page.header}\n\n")

            # Add main content
            markdown_parts.append(page.markdown)
            markdown_parts.append("\n\n")

            # Add tables in HTML format
            if page.tables:
                markdown_parts.append(f"### Tables on Page {page.index + 1}\n\n")
                for table in page.tables:
                    markdown_parts.append(f"**Table {table.id}:**\n\n")
                    markdown_parts.append(table.content)
                    markdown_parts.append("\n\n")

            # Add footer if present
            if page.footer:
                markdown_parts.append(f"**Footer:** {page.footer}\n\n")

            markdown_parts.append("---\n\n")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(''.join(markdown_parts))

        logger.info(
            "Markdown saved",
            output=output_path.name,
            size_kb=round(output_path.stat().st_size / 1024, 2)
        )

    def annotate_pages(
        self,
        pdf_path: Path,
        page_numbers: list[int],
        annotation_schema: type[BaseModel],
        annotation_prompt: str | None = None
    ) -> dict[str, Any]:
        """
        Extract specific pages with schema-based annotation and confidence scores.

        This uses Mistral's Document Annotation feature for intelligence extraction
        on edge cases flagged by Gemini. Limited to 8 pages per call.

        Args:
            pdf_path: Path to the PDF file
            page_numbers: List of page numbers to extract (0-indexed)
            annotation_schema: Pydantic model defining the extraction schema
            annotation_prompt: Optional high-level prompt to guide annotation

        Returns:
            Dictionary with annotated data and confidence scores

        Example:
            >>> from pydantic import BaseModel, Field
            >>> class SalaryTable(BaseModel):
            ...     functiegroep: str = Field(description="Job classification group")
            ...     salary_amount: float = Field(description="Monthly salary in euros")
            ...     confidence: float = Field(description="Confidence score 0.0-1.0")
            ...
            >>> result = ocr.annotate_pages(
            ...     pdf_path,
            ...     page_numbers=[39, 40],  # Pages with salary tables
            ...     annotation_schema=SalaryTable,
            ...     annotation_prompt="Extract salary scales with confidence scores"
            ... )

        Raises:
            ValueError: If more than 8 pages requested (Mistral limit)
        """
        if len(page_numbers) > 8:
            raise ValueError(
                f"Document annotation limited to 8 pages, got {len(page_numbers)}. "
                "Split into multiple calls or use basic OCR."
            )

        logger.info(
            "Annotating pages with schema",
            pdf=pdf_path.name,
            pages=page_numbers,
            schema=annotation_schema.__name__
        )

        # Encode PDF to base64
        with open(pdf_path, "rb") as f:
            pdf_base64 = base64.b64encode(f.read()).decode('utf-8')

        # Convert Pydantic schema to JSON schema
        json_schema = annotation_schema.model_json_schema()

        # Build annotation request (SDK expects list of ints for pages)
        request_params = {
            "model": self.model,
            "document": {
                "type": "document_url",
                "document_url": f"data:application/pdf;base64,{pdf_base64}"
            },
            "document_annotation_format": json_schema,
            "pages": page_numbers  # SDK expects List[int]
        }

        # Add optional prompt
        if annotation_prompt:
            request_params["document_annotation_prompt"] = annotation_prompt

        # Call Mistral Document Annotation API
        try:
            response = self.client.ocr.process(**request_params)

            logger.info(
                "Page annotation complete",
                pages=len(page_numbers),
                model=response.model
            )

            return {
                "model": response.model,
                "pages": page_numbers,
                "schema": annotation_schema.__name__,
                "annotations": response.annotations if hasattr(response, 'annotations') else None,
                "raw_response": response
            }

        except Exception as e:
            logger.error(
                "Document annotation failed",
                error=str(e),
                pages=page_numbers
            )
            raise
