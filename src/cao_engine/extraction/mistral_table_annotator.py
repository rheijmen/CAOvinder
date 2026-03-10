"""Mistral Document AI Table Annotator - Extract salary scales and remuneration tables.

This module uses Mistral Document AI's document_annotation feature to extract
structured salary table data from CAO PDFs with schema enforcement.

Focus: Loongebouw (salary structures), functiegroepen, schalen, treden, periodieken
"""

import base64
import os
from pathlib import Path

import structlog
from mistralai import Mistral
from mistralai.extra import response_format_from_pydantic_model
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class SalaryStep(BaseModel):
    """Individual salary step within a scale (periodiek/trede)."""
    step_number: int | None = Field(None, description="Step number (0, 1, 2...)")
    value: float = Field(..., description="Monthly salary amount in EUR")


class SalaryScale(BaseModel):
    """One salary scale/functiegroep (e.g., Group A, Schaal 5)."""
    name: str = Field(..., description="Scale name (e.g., 'Group A', 'Schaal 5', 'FWG 3')")
    min_value: float = Field(..., description="Minimum monthly salary in EUR")
    max_value: float = Field(..., description="Maximum monthly salary in EUR")
    steps: list[SalaryStep] = Field(default_factory=list, description="Salary steps (periodieken)")
    effective_date: str | None = Field(None, description="Date this scale becomes effective (ISO format)")
    work_duration_hours: float | None = Field(None, description="Full-time hours per week (e.g., 38, 40)")


class RemunerationTableExtraction(BaseModel):
    """Structured extraction of ALL salary tables from CAO document."""
    cao_name: str = Field(..., description="Official CAO name")
    effective_period_start: str = Field(..., description="CAO start date (ISO format)")
    effective_period_end: str = Field(..., description="CAO end date (ISO format)")
    salary_scales: list[SalaryScale] = Field(..., description="ALL salary scales found in document")
    currency: str = Field(default="EUR", description="Currency code")
    interval: str = Field(default="Month", description="Payment interval (Month, Week, Hour)")
    confidence_score: float | None = Field(None, description="Overall confidence (0-1) - set to None if not applicable")
    extraction_notes: list[str] = Field(
        default_factory=list,
        description="Notes about extraction challenges or ambiguities"
    )


TABLE_ANNOTATION_PROMPT = """Extract ALL salary scales and remuneration tables from this Dutch CAO document.

CRITICAL: Focus on LOONGEBOUW sections with salary tables showing:
- Functiegroep/Schaal names (A, B, C or 1, 2, 3 or FWG 1, FWG 2...)
- Minimum and maximum monthly amounts (bruto maandsalaris)
- Periodieken/treden (salary steps between min and max)
- Effective dates (ingangsdatum, peildatum)

DUTCH TERMINOLOGY TO RECOGNIZE:
- Loonschaal = Salary scale
- Functiegroep = Job classification group
- Trede/Periodiek = Salary step
- Minimum/Maximum = Min/max salary in scale
- Bruto maandsalaris = Gross monthly salary
- Peildatum = Effective date
- Fulltime = Full-time (usually 38-40 hours/week)

EXTRACTION RULES:
1. Extract EVERY salary table you find (there may be multiple for different periods)
2. For each scale, capture: name, min, max, ALL steps
3. If table shows "per maand bij fulltime" → interval = "Month", workDuration = 38 or 40
4. If unclear which hours = fulltime, use 40 as default
5. Convert all amounts to float (remove €, remove thousand separators, use . for decimals)
6. If table has merged cells or complex structure, extract ALL rows you can identify
7. If multiple tables with different effective dates, extract ALL of them
8. If confidence < 0.85 on any field, add note to extraction_notes

OUTPUT REQUIREMENTS:
- Return ALL salary scales found (typically 5-15 scales per CAO)
- Include ALL periodieken for each scale (typically 0-12 steps)
- Use EXACT scale names from document (don't translate or normalize)
- Set confidence_score to lowest field confidence
- Add extraction_notes if anything unclear or ambiguous

Be thorough and complete. This data drives payroll compliance.
"""


class MistralTableAnnotator:
    """Extract salary tables using Mistral Document AI's document_annotation feature."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY environment variable not set")

        self.client = Mistral(api_key=self.api_key)
        self.model = "mistral-ocr-latest"

    def extract_tables_from_pdf(self, pdf_path: Path, cao_name: str) -> RemunerationTableExtraction:
        """
        Extract salary tables directly from PDF using document annotation.

        Args:
            pdf_path: Path to CAO PDF file
            cao_name: Official CAO name for metadata

        Returns:
            RemunerationTableExtraction with all salary scales
        """
        logger.info("Starting Mistral table annotation", pdf_path=str(pdf_path), cao=cao_name)

        # Encode PDF to base64
        with open(pdf_path, "rb") as f:
            pdf_base64 = base64.b64encode(f.read()).decode('utf-8')

        # Build document annotation request
        try:
            response = self.client.ocr.process(
                model=self.model,
                document={
                    "type": "document_url",
                    "document_url": f"data:application/pdf;base64,{pdf_base64}"
                },
                table_format="html",  # Extract tables as HTML for better structure
                document_annotation_format=response_format_from_pydantic_model(RemunerationTableExtraction),
                document_annotation_prompt=TABLE_ANNOTATION_PROMPT
            )

            # Extract annotated result
            if not response.document_annotation:
                raise ValueError("No document annotation returned from Mistral API")

            # Convert to Pydantic model (handle string or dict response)
            annotation_data = response.document_annotation
            if isinstance(annotation_data, str):
                import json
                annotation_data = json.loads(annotation_data)

            result = RemunerationTableExtraction.model_validate(annotation_data)

            logger.info(
                "Mistral table annotation complete",
                cao=cao_name,
                scales_extracted=len(result.salary_scales),
                confidence=result.confidence_score
            )

            return result

        except Exception as e:
            logger.error("Mistral table annotation failed", error=str(e), cao=cao_name)
            raise

    def extract_tables_from_ocr(
        self,
        ocr_markdown: str,
        pdf_path: Path,
        cao_name: str
    ) -> RemunerationTableExtraction:
        """
        Extract salary tables from already-processed OCR output.

        This is useful when we already have OCR markdown and just want to
        run document annotation on it (faster than re-processing PDF).

        Args:
            ocr_markdown: OCR markdown text with HTML tables
            pdf_path: Original PDF path (for page extraction if needed)
            cao_name: Official CAO name

        Returns:
            RemunerationTableExtraction with all salary scales
        """
        logger.info("Extracting tables from OCR markdown", cao=cao_name)

        # For now, fall back to PDF extraction since Mistral Document AI
        # requires the actual document, not just markdown
        # TODO: Investigate if Mistral supports annotation on text-only input
        return self.extract_tables_from_pdf(pdf_path, cao_name)
