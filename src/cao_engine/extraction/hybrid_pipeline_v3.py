"""Hybrid Pipeline V3 - Mistral Table Annotation + Gemini 3.0 Flash Preview.

New architecture:
1. Mistral Document AI → Extract salary tables with document_annotation (schema-enforced)
2. Gemini 3.0 Flash Preview → Extract complete SETU v2.0 (1M context, thinking mode)
3. Merge: Use Mistral tables (high confidence) + Gemini rest (flexibility)

Benefits:
- Mistral guarantees correct table structure (Pydantic schema enforcement)
- Gemini handles full document complexity (allowances, leave, pension, etc.)
- No 3-LLM pipeline complexity (Review + Judge removed)
- Faster: 2 API calls instead of 4
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import structlog

from .gemini_rest_api import GeminiRestAPIExtractor
from .mistral_table_annotator import MistralTableAnnotator, RemunerationTableExtraction

logger = structlog.get_logger(__name__)


@dataclass
class HybridExtractionResult:
    """Result from hybrid Mistral + Gemini extraction."""
    setu_data: dict  # Final merged SETU v2.0 JSON
    table_extraction: RemunerationTableExtraction  # Mistral table annotation
    gemini_full: dict  # Gemini complete extraction
    confidence_score: float  # Overall confidence (0-1)
    merge_notes: list[str]  # Notes about merge decisions


class HybridPipelineV3:
    """
    Hybrid pipeline combining Mistral table annotation with Gemini full extraction.

    Strategy:
    1. Mistral Document AI annotates salary tables (schema-enforced, high confidence)
    2. Gemini 3.0 Flash Preview extracts complete SETU (full document understanding)
    3. Merge: Prefer Mistral for remuneration.salaryScale, Gemini for everything else
    """

    def __init__(
        self,
        mistral_api_key: str,
        gemini_api_key: str,
        gemini_model: str = "gemini-3-flash-preview",
        gemini_thinking_level: str = "MEDIUM"
    ):
        self.mistral_annotator = MistralTableAnnotator(api_key=mistral_api_key)
        self.gemini_extractor = GeminiRestAPIExtractor(
            api_key=gemini_api_key,
            model=gemini_model,
            thinking_mode=gemini_thinking_level
        )
        logger.info(
            "Hybrid Pipeline V3 initialized",
            gemini_model=gemini_model,
            gemini_thinking=gemini_thinking_level
        )

    def extract(
        self,
        pdf_path: Path,
        markdown_path: Path,
        cao_name: str
    ) -> HybridExtractionResult:
        """
        Run hybrid extraction pipeline.

        Args:
            pdf_path: Path to original CAO PDF (for Mistral annotation)
            markdown_path: Path to OCR markdown (for Gemini)
            cao_name: Official CAO name

        Returns:
            HybridExtractionResult with merged SETU data
        """
        logger.info(
            "Starting Hybrid Pipeline V3",
            cao=cao_name,
            pdf=str(pdf_path),
            markdown=str(markdown_path)
        )

        # Step 1: Mistral Document AI - Extract salary tables with schema enforcement
        logger.info("Step 1/3: Mistral table annotation", cao=cao_name)
        table_extraction = self.mistral_annotator.extract_tables_from_pdf(pdf_path, cao_name)

        logger.info(
            "Mistral table annotation complete",
            scales_extracted=len(table_extraction.salary_scales),
            confidence=table_extraction.confidence_score
        )

        # Step 2: Gemini 3.0 Flash Preview - Extract complete SETU v2.0
        logger.info("Step 2/3: Gemini 3.0 full extraction", cao=cao_name)
        markdown_text = markdown_path.read_text(encoding="utf-8")
        gemini_full = self.gemini_extractor.extract(markdown_text, cao_name)

        logger.info(
            "Gemini full extraction complete",
            has_remuneration=bool(gemini_full.get("remuneration")),
            has_allowances=bool(gemini_full.get("allowance"))
        )

        # Step 3: Intelligent merge
        logger.info("Step 3/3: Merging Mistral tables + Gemini full", cao=cao_name)
        merged, merge_notes = self._merge_extractions(table_extraction, gemini_full, cao_name)

        # Calculate overall confidence
        confidence = self._calculate_confidence(table_extraction, gemini_full, merge_notes)

        result = HybridExtractionResult(
            setu_data=merged,
            table_extraction=table_extraction,
            gemini_full=gemini_full,
            confidence_score=confidence,
            merge_notes=merge_notes
        )

        logger.info(
            "Hybrid Pipeline V3 complete",
            cao=cao_name,
            confidence=confidence,
            merge_notes_count=len(merge_notes)
        )

        return result

    def _merge_extractions(
        self,
        table_extraction: RemunerationTableExtraction,
        gemini_full: dict,
        cao_name: str
    ) -> tuple[dict, list[str]]:
        """
        Merge Mistral table annotation with Gemini full extraction.

        Strategy:
        - Use Mistral for remuneration.salaryScale (schema-enforced, high confidence)
        - Use Gemini for everything else (allowances, leave, pension, etc.)
        - Convert Mistral SalaryScale format to SETU Remuneration format
        """
        merge_notes = []

        # Start with Gemini's full extraction as base
        merged = gemini_full.copy()

        # Convert Mistral salary scales to SETU Remuneration format
        if table_extraction.salary_scales:
            setu_remuneration = self._convert_mistral_tables_to_setu(table_extraction)

            # Replace Gemini's remuneration with Mistral's (higher confidence)
            if setu_remuneration:
                merged["remuneration"] = setu_remuneration
                merge_notes.append(
                    f"Replaced remuneration with Mistral table annotation "
                    f"({len(table_extraction.salary_scales)} scales, "
                    f"confidence={table_extraction.confidence_score:.2f})"
                )
            else:
                merge_notes.append(
                    "Mistral table extraction found scales but conversion to SETU failed, "
                    "using Gemini remuneration"
                )
        else:
            merge_notes.append(
                "No salary scales found by Mistral, using Gemini remuneration"
            )

        # Add merge metadata
        merged["_hybrid_pipeline_metadata"] = {
            "cao_name": cao_name,
            "pipeline_version": "v3",
            "extracted_at": datetime.now().isoformat(),
            "mistral_tables_used": bool(table_extraction.salary_scales),
            "mistral_scales_count": len(table_extraction.salary_scales),
            "mistral_confidence": table_extraction.confidence_score,
            "merge_notes": merge_notes
        }

        return merged, merge_notes

    def _convert_mistral_tables_to_setu(
        self,
        table_extraction: RemunerationTableExtraction
    ) -> list[dict]:
        """
        Convert Mistral's SalaryScale format to SETU v2.0 Remuneration format.

        Mistral format:
        {
            "salary_scales": [{
                "name": "Group A",
                "min_value": 2847.50,
                "max_value": 3621.00,
                "steps": [{"step_number": 0, "value": 2847.50}, ...]
            }]
        }

        SETU format:
        {
            "remuneration": [{
                "origin": {"type": "CollectiveLabourAgreement"},
                "salaryScale": [{
                    "name": "Group A",
                    "minValue": 2847.50,
                    "maxValue": 3621.00,
                    "interval": "Month",
                    "salaryStep": [{"value": 2847.50}, ...]
                }]
            }]
        }
        """
        remuneration_list = []

        # Group all scales under single remuneration object
        salary_scales_setu = []
        for scale in table_extraction.salary_scales:
            # Convert steps to SETU format
            salary_steps_setu = [
                {"value": step.value}
                for step in scale.steps
            ]

            salary_scale_setu = {
                "name": scale.name,
                "minValue": scale.min_value,
                "maxValue": scale.max_value,
                "interval": table_extraction.interval,  # "Month", "Week", "Hour"
                "currency": {"code": table_extraction.currency}  # "EUR"
            }

            # Add steps if present
            if salary_steps_setu:
                salary_scale_setu["salaryStep"] = salary_steps_setu

            # Add work duration if specified
            if scale.work_duration_hours:
                salary_scale_setu["workDuration"] = {
                    "value": scale.work_duration_hours,
                    "unit": "Hour"
                }

            # Add effective date if specified
            if scale.effective_date:
                salary_scale_setu["effectiveDate"] = scale.effective_date

            salary_scales_setu.append(salary_scale_setu)

        # Wrap in SETU remuneration structure
        if salary_scales_setu:
            remuneration_obj = {
                "origin": {
                    "type": "CollectiveLabourAgreement"
                },
                "salaryScale": salary_scales_setu
            }

            # Add effective period if available
            if table_extraction.effective_period_start and table_extraction.effective_period_end:
                remuneration_obj["effectivePeriod"] = {
                    "start": table_extraction.effective_period_start,
                    "end": table_extraction.effective_period_end
                }

            remuneration_list.append(remuneration_obj)

        return remuneration_list

    def _calculate_confidence(
        self,
        table_extraction: RemunerationTableExtraction,
        gemini_full: dict,
        merge_notes: list[str]
    ) -> float:
        """
        Calculate overall confidence score for hybrid extraction.

        Factors:
        - Mistral table confidence (0-1)
        - Gemini extraction completeness (has key fields?)
        - Merge success (were tables successfully converted?)
        """
        scores = []

        # Mistral table confidence (high weight for salary data)
        mistral_confidence = table_extraction.confidence_score if table_extraction.confidence_score is not None else 0.8
        scores.append(mistral_confidence * 0.5)  # 50% weight

        # Gemini completeness (25% weight)
        gemini_completeness = 0.0
        if gemini_full.get("documentId"):
            gemini_completeness += 0.2
        if gemini_full.get("effectivePeriod"):
            gemini_completeness += 0.2
        if gemini_full.get("remuneration"):
            gemini_completeness += 0.2
        if gemini_full.get("allowance"):
            gemini_completeness += 0.2
        if gemini_full.get("leave"):
            gemini_completeness += 0.2
        scores.append(gemini_completeness * 0.25)

        # Merge success (25% weight)
        merge_success = 1.0
        if "conversion to SETU failed" in " ".join(merge_notes):
            merge_success = 0.5
        if "No salary scales found" in " ".join(merge_notes):
            merge_success = 0.7
        scores.append(merge_success * 0.25)

        overall = sum(scores)
        return round(overall, 2)
