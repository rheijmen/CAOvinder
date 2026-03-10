"""Hybrid Pipeline: Mistral Document AI (tables) + Mistral Large (full SETU).

This is a pure-Mistral solution:
1. Mistral Document AI - Extract salary scales from PDF (WORKING ✅)
2. Mistral Large - Extract complete SETU v2.0 from markdown
3. Intelligent merge - Combine structured tables with full extraction

Benefits:
- NO Gemini schema limitations
- Consistent Mistral API
- Proven to work
- Table annotation provides high-quality structured data for salary scales
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import structlog

from .mistral_reviewer import MistralReviewer
from .mistral_table_annotator import MistralTableAnnotator, RemunerationTableExtraction

logger = structlog.get_logger(__name__)


@dataclass
class HybridExtractionResult:
    """Result from hybrid extraction."""
    setu_data: dict
    table_extraction: RemunerationTableExtraction
    mistral_full: dict
    merge_notes: list[str]
    elapsed_seconds: float


class HybridPipelineMistral:
    """Hybrid extraction pipeline using only Mistral AI."""

    def __init__(self, mistral_api_key: str, mistral_model: str = "mistral-large-latest"):
        """Initialize hybrid pipeline with Mistral AI.

        Args:
            mistral_api_key: Mistral API key
            mistral_model: Mistral model for full extraction (default: mistral-large-latest)
        """
        self.mistral_annotator = MistralTableAnnotator(api_key=mistral_api_key)
        self.mistral_extractor = MistralReviewer(api_key=mistral_api_key, model=mistral_model)

        logger.info(
            "Hybrid Pipeline MISTRAL initialized",
            mistral_model=mistral_model,
        )

    def extract(
        self,
        pdf_path: Path,
        markdown_path: Path,
        cao_name: str,
    ) -> HybridExtractionResult:
        """Extract SETU v2.0 using hybrid Mistral pipeline.

        Args:
            pdf_path: Path to CAO PDF
            markdown_path: Path to OCR markdown
            cao_name: CAO name for metadata

        Returns:
            HybridExtractionResult with merged SETU data
        """
        start_time = datetime.now()

        logger.info(
            "Starting Hybrid Pipeline MISTRAL",
            cao=cao_name,
            pdf=str(pdf_path),
            markdown=str(markdown_path),
        )

        # Step 1: Mistral Document AI - Extract salary tables from PDF
        logger.info("Step 1/3: Mistral Document AI table annotation", cao=cao_name)
        table_extraction = self.mistral_annotator.extract_tables_from_pdf(pdf_path, cao_name)

        logger.info(
            "Mistral table annotation complete",
            scales_extracted=len(table_extraction.salary_scales),
            confidence=table_extraction.confidence_score,
        )

        # Step 2: Mistral Large - Extract complete SETU v2.0 from markdown
        logger.info("Step 2/3: Mistral Large full extraction", cao=cao_name)
        markdown_text = markdown_path.read_text(encoding="utf-8")

        # Mistral Reviewer expects gemini_output, but we'll pass empty dict
        # It will do its own extraction
        mistral_full = self.mistral_extractor.review(
            markdown=markdown_text,
            gemini_output={},  # No Gemini - Mistral will extract from scratch
            cao_name=cao_name
        )

        logger.info(
            "Mistral full extraction complete",
            has_remuneration="remuneration" in mistral_full,
            has_allowances="allowance" in mistral_full,
        )

        # Step 3: Intelligent merge - Combine table annotation with full extraction
        logger.info("Step 3/3: Merging extractions", cao=cao_name)
        merged_setu, merge_notes = self._merge_extractions(
            table_extraction,
            mistral_full,
            cao_name,
        )

        elapsed = (datetime.now() - start_time).total_seconds()

        logger.info(
            "Hybrid Pipeline MISTRAL complete",
            cao=cao_name,
            elapsed_seconds=elapsed,
            merge_notes_count=len(merge_notes),
        )

        return HybridExtractionResult(
            setu_data=merged_setu,
            table_extraction=table_extraction,
            mistral_full=mistral_full,
            merge_notes=merge_notes,
            elapsed_seconds=elapsed,
        )

    def _normalize_setu_schema(self, setu_dict: dict) -> dict:
        """Normalize Mistral Large output to strict SETU v2.0 schema.

        Mistral Large often produces schema-invalid structures like:
        - documentId/versionId as strings instead of objects
        - customer.legalId as string instead of array
        - personContacts[].name as string instead of object
        - interval as string instead of object
        - workDuration with wrong field names (value/unit vs amount/interval/valuePerWeek)
        - leave/pension as non-arrays
        - salaryStep names as integers instead of strings

        Args:
            setu_dict: SETU document from Mistral Large

        Returns:
            Schema-normalized SETU document
        """
        normalized = setu_dict.copy()

        # Fix documentId and versionId - convert strings to objects
        if "documentId" in normalized and isinstance(normalized["documentId"], str):
            normalized["documentId"] = {"value": normalized["documentId"]}
        if "versionId" in normalized and isinstance(normalized["versionId"], str):
            normalized["versionId"] = {"value": normalized["versionId"]}

        # CRITICAL: Fix schemeAgencyId enum values (SETU v2.0 official validator requirement)
        if "documentId" in normalized and isinstance(normalized["documentId"], dict):
            # documentId.schemeAgencyId must be "Customer" or "Supplier"
            if "schemeAgencyId" not in normalized["documentId"]:
                normalized["documentId"]["schemeAgencyId"] = "Customer"
            elif normalized["documentId"]["schemeAgencyId"] not in ["Customer", "Supplier"]:
                # Fix common mistakes like "CAO-NL", "SETU", etc.
                normalized["documentId"]["schemeAgencyId"] = "Customer"

        # Fix customer section
        if "customer" in normalized:
            customer = normalized["customer"]

            # Fix legalId - convert string to array
            if "legalId" in customer and isinstance(customer["legalId"], str):
                customer["legalId"] = [{"value": customer["legalId"], "schemeAgencyId": "KvK"}]
            elif "legalId" in customer and isinstance(customer["legalId"], list):
                # Ensure each item is an object
                fixed_legal_ids = []
                for item in customer["legalId"]:
                    if isinstance(item, str):
                        fixed_legal_ids.append({"value": item, "schemeAgencyId": "KvK"})
                    else:
                        # CRITICAL: Fix schemeAgencyId enum for legalId (must be "KvK", "OIN", or "RSIN")
                        if "schemeAgencyId" not in item:
                            item["schemeAgencyId"] = "KvK"
                        elif item["schemeAgencyId"] not in ["KvK", "OIN", "RSIN"]:
                            # Fix common mistakes like "KVK-NL", "KVK", "0106", etc.
                            item["schemeAgencyId"] = "KvK"
                        fixed_legal_ids.append(item)
                customer["legalId"] = fixed_legal_ids

            # Fix personContacts - ensure name is object
            if "personContacts" in customer:
                for contact in customer["personContacts"]:
                    if "name" in contact and isinstance(contact["name"], str):
                        contact["name"] = {"formattedName": contact["name"]}

                    # CRITICAL: Fix "role" → "roleCode" (SETU v2.0 requirement)
                    if "role" in contact and "roleCode" not in contact:
                        contact["roleCode"] = contact.pop("role")

        # Fix leave array
        if "leave" in normalized and not isinstance(normalized["leave"], list):
            if normalized["leave"] is None:
                normalized["leave"] = []
            else:
                normalized["leave"] = [normalized["leave"]]

        # Fix pension array
        if "pension" in normalized and not isinstance(normalized["pension"], list):
            if normalized["pension"] is None:
                normalized["pension"] = []
            else:
                normalized["pension"] = [normalized["pension"]]

        # Fix remuneration section
        if "remuneration" in normalized:
            for remun_item in normalized["remuneration"]:
                # Fix interval - convert string to object
                if "interval" in remun_item and isinstance(remun_item["interval"], str):
                    remun_item["interval"] = {"code": remun_item["interval"]}

                # Fix workDuration - convert {value, unit} to {amount, interval, valuePerWeek}
                if "workDuration" in remun_item:
                    wd = remun_item["workDuration"]
                    # Check if it's a dict (could be string in some malformed cases)
                    if isinstance(wd, dict):
                        if "value" in wd and "amount" not in wd:
                            # Old format: {value: 38, unit: "Hour"}
                            # New format: {amount: 38, interval: {code: "Week"}, valuePerWeek: 38}
                            remun_item["workDuration"] = {
                                "amount": wd.get("value", 40),
                                "interval": {"code": "Week"},
                                "valuePerWeek": wd.get("value", 40),
                            }
                    else:
                        # Malformed - create default structure
                        remun_item["workDuration"] = {
                            "amount": 40,
                            "interval": {"code": "Week"},
                            "valuePerWeek": 40,
                        }

                # Fix salary scales
                if "salaryScale" in remun_item:
                    for scale in remun_item["salaryScale"]:
                        # Fix salaryStep names - convert integers to strings
                        if "salaryStep" in scale:
                            for step in scale["salaryStep"]:
                                if "name" in step and isinstance(step["name"], (int, float)):
                                    step["name"] = str(int(step["name"]))

                        # Fix missing currency - add EUR as default
                        if "currency" not in scale:
                            scale["currency"] = "EUR"

        return normalized

    def _merge_extractions(
        self,
        table_extraction: RemunerationTableExtraction,
        mistral_full: dict,
        cao_name: str,
    ) -> tuple[dict, list[str]]:
        """Intelligently merge table annotation with full extraction.

        Strategy:
        - Prefer Mistral Document AI tables for salary scales (high confidence)
        - Use Mistral Large for everything else
        - Normalize Mistral Large output to strict SETU v2.0 schema
        - Document merge decisions in notes

        Args:
            table_extraction: Structured tables from Mistral Document AI
            mistral_full: Complete SETU from Mistral Large
            cao_name: CAO name

        Returns:
            Tuple of (merged_setu_dict, merge_notes)
        """
        merge_notes = []

        # Normalize Mistral Large output to strict SETU v2.0 schema
        mistral_normalized = self._normalize_setu_schema(mistral_full)

        # Start with normalized Mistral Large extraction as base
        merged = mistral_normalized.copy()

        # Convert Mistral table annotation to SETU format
        table_remuneration = self._convert_mistral_tables_to_setu(table_extraction)

        # Check if Mistral Large has remuneration
        mistral_remuneration = mistral_full.get("remuneration", [])

        if table_extraction.confidence_score and table_extraction.confidence_score >= 0.85:
            # HIGH CONFIDENCE: Use table annotation for salary scales
            merged["remuneration"] = table_remuneration
            merge_notes.append(
                f"Used Mistral Document AI tables (confidence {table_extraction.confidence_score:.2f}, "
                f"{len(table_extraction.salary_scales)} scales)"
            )

            if mistral_remuneration:
                merge_notes.append(
                    f"Replaced Mistral Large remuneration ({len(mistral_remuneration)} items) "
                    f"with high-confidence table annotation"
                )

        elif not mistral_remuneration and table_extraction.salary_scales:
            # Mistral Large missed salary scales - use table annotation as fallback
            merged["remuneration"] = table_remuneration
            merge_notes.append(
                f"Mistral Large had no remuneration - used table annotation fallback "
                f"({len(table_extraction.salary_scales)} scales, confidence "
                f"{table_extraction.confidence_score or 'unknown'})"
            )

        else:
            # Use Mistral Large's extraction
            merge_notes.append(
                f"Used Mistral Large remuneration ({len(mistral_remuneration)} items)"
            )

            if table_extraction.salary_scales:
                merge_notes.append(
                    f"Table annotation found {len(table_extraction.salary_scales)} scales "
                    f"but confidence was low ({table_extraction.confidence_score or 'unknown'})"
                )

        # Add hybrid metadata
        merged["_hybrid_extraction"] = {
            "pipeline": "mistral-hybrid",
            "cao_name": cao_name,
            "table_annotator": {
                "model": "mistral-ocr-latest",
                "confidence": table_extraction.confidence_score,
                "scales_found": len(table_extraction.salary_scales),
            },
            "full_extractor": {
                "model": mistral_full.get("_extraction_metadata", {}).get("model", "mistral-large-latest"),
                "remuneration_items": len(mistral_remuneration),
            },
            "merge_notes": merge_notes,
            "extracted_at": datetime.now().isoformat(),
        }

        # CRITICAL: Remove non-SETU properties before returning (for official validator compliance)
        merged_clean = self._remove_non_setu_properties(merged)

        return merged_clean, merge_notes

    def _remove_non_setu_properties(self, setu_dict: dict) -> dict:
        """Remove all properties not in SETU v2.0 InquiryPayEquity specification.

        The official SETU validator has `additionalProperties: false`, so any fields
        not in the spec will cause validation errors.

        SETU v2.0 InquiryPayEquity allowed root properties (18 total):
        - documentId, versionId, effectivePeriod, customer
        - remuneration, leave, pension, benefits
        - workingConditions, training, careerDevelopment
        - healthAndSafety, disputeResolution, termination
        - dataProtection, amendments, signatures, attachments
        """
        ALLOWED_ROOT_PROPERTIES = {
            "documentId", "versionId", "effectivePeriod", "customer",
            "remuneration", "leave", "pension", "benefits",
            "workingConditions", "training", "careerDevelopment",
            "healthAndSafety", "disputeResolution", "termination",
            "dataProtection", "amendments", "signatures", "attachments",
        }

        # Create clean dict with only allowed properties
        clean_dict = {k: v for k, v in setu_dict.items() if k in ALLOWED_ROOT_PROPERTIES}

        return clean_dict

    def _convert_mistral_tables_to_setu(
        self,
        table_extraction: RemunerationTableExtraction,
    ) -> list[dict]:
        """Convert Mistral table format to SETU v2.0 remuneration format.

        Args:
            table_extraction: Tables from Mistral Document AI

        Returns:
            List of SETU remuneration items
        """
        salary_scales_setu = []

        for idx, scale in enumerate(table_extraction.salary_scales):
            # Convert salary steps - each step needs a name (must be string per SETU v2.0 schema)
            salary_steps_setu = []
            for step_idx, step in enumerate(scale.steps):
                # Convert step number to string - SETU v2.0 requires string type
                step_name = (
                    str(int(step.step_number))
                    if step.step_number is not None
                    else f"Step {step_idx}"
                )
                salary_steps_setu.append({
                    "name": step_name,
                    "value": step.value,
                })

            # Build SETU salary scale
            # NOTE: interval and workDuration go on remuneration level
            salary_scale_setu = {
                "name": scale.name,
                "minValue": scale.min_value,
                "maxValue": scale.max_value,
                "currency": table_extraction.currency or "EUR",  # Required field
            }

            # Add steps if present
            if salary_steps_setu:
                salary_scale_setu["salaryStep"] = salary_steps_setu

            # Add effective date if present
            if scale.effective_date:
                salary_scale_setu["effectivePeriod"] = {
                    "start": scale.effective_date,
                }

            salary_scales_setu.append(salary_scale_setu)

        # Wrap in SETU remuneration structure with STRICT v2.0 schema
        # Required fields at remuneration level: workDuration (object), interval (object)
        work_hours = (
            table_extraction.salary_scales[0].work_duration_hours
            if table_extraction.salary_scales and table_extraction.salary_scales[0].work_duration_hours
            else 40
        )

        remuneration_item = {
            "origin": {
                "type": "CollectiveLabourAgreement",
            },
            "workDuration": {
                "amount": {
                    "value": work_hours,
                    "unitCode": "Hour"
                },
                "interval": {
                    "value": 1,
                    "unitCode": "Week"
                },
                "valuePerWeek": work_hours,
            },
            "interval": {
                "value": 1,
                "unitCode": table_extraction.interval
            },
            "salaryScale": salary_scales_setu,
        }

        return [remuneration_item]
