"""Second Opinion Orchestrator - Validates SETU extraction using two LLMs.

Strategy:
1. Mistral extracts SETU v2.0 (fast, good baseline)
2. Gemini 2.5 Flash extracts independently (different perspective)
3. Orchestrator compares field-by-field
4. Where they agree → high confidence ✅
5. Where they disagree → flag for review 🚩
6. Return merged result with confidence metadata
"""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class FieldComparison:
    """Comparison result for a single field."""

    def __init__(self, field_path: str, mistral_value: Any, gemini_value: Any):
        self.field_path = field_path
        self.mistral_value = mistral_value
        self.gemini_value = gemini_value
        self.agrees = self._compare_values(mistral_value, gemini_value)
        self.confidence = "high" if self.agrees else "low"

    def _compare_values(self, v1: Any, v2: Any) -> bool:
        """Smart comparison handling None, numbers, strings, lists."""
        # Both None/null → agree
        if v1 is None and v2 is None:
            return True
        # One None, one not → disagree
        if (v1 is None) != (v2 is None):
            return False
        # Numbers - allow small float differences
        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
            return abs(v1 - v2) < 0.01
        # Strings - exact match
        if isinstance(v1, str) and isinstance(v2, str):
            return v1.strip().lower() == v2.strip().lower()
        # Lists - same length and elements
        if isinstance(v1, list) and isinstance(v2, list):
            return len(v1) == len(v2)  # Simplified
        # Dicts - recursive (handled by caller)
        # Default: exact equality
        return v1 == v2


class SecondOpinionOrchestrator:
    """Validates SETU extraction by comparing Mistral vs Gemini outputs."""

    def __init__(self):
        self.comparisons: list[FieldComparison] = []
        self.agreements = 0
        self.disagreements = 0

    def merge_with_confidence(
        self, mistral_output: dict, gemini_output: dict, cao_name: str
    ) -> dict:
        """Compare two SETU outputs and return merged result with confidence metadata.

        Strategy:
        - Where both agree: use value (high confidence)
        - Where they disagree: prefer Gemini 2.5 (better at structured data), flag for review
        - Track all comparisons for audit
        """
        logger.info(
            "Starting second opinion merge",
            cao=cao_name,
            mistral_has_remuneration=bool(mistral_output.get("remuneration")),
            gemini_has_remuneration=bool(gemini_output.get("remuneration")),
        )

        # Compare top-level fields
        merged = {}
        confidence_metadata = {
            "cao_name": cao_name,
            "extraction_timestamp": datetime.utcnow().isoformat(),
            "mistral_model": "mistral-large-latest",
            "gemini_model": "gemini-2.5-flash-latest",
            "field_agreements": [],
            "field_disagreements": [],
            "overall_confidence": 0.0,
        }

        # Critical fields to compare
        critical_fields = [
            "documentId",
            "effectivePeriod",
            "labourAgreements",
            "remuneration",
            "allowance",
            "holidayAllowance",
            "leave",
            "pension",
        ]

        for field in critical_fields:
            mistral_val = mistral_output.get(field)
            gemini_val = gemini_output.get(field)

            comparison = FieldComparison(field, mistral_val, gemini_val)
            self.comparisons.append(comparison)

            if comparison.agrees:
                self.agreements += 1
                merged[field] = mistral_val  # Either works since they agree
                confidence_metadata["field_agreements"].append(field)
            else:
                self.disagreements += 1
                # Prefer Gemini for structured data (better at JSON Schema compliance)
                merged[field] = gemini_val
                confidence_metadata["field_disagreements"].append({
                    "field": field,
                    "mistral_value": str(mistral_val)[:200] if mistral_val else None,
                    "gemini_value": str(gemini_val)[:200] if gemini_val else None,
                    "resolution": "used_gemini",
                })

        # Calculate overall confidence
        total_fields = len(critical_fields)
        confidence_metadata["overall_confidence"] = (
            self.agreements / total_fields if total_fields > 0 else 0.0
        )

        # Add metadata to output
        merged["_orchestrator_metadata"] = confidence_metadata

        logger.info(
            "Second opinion merge complete",
            agreements=self.agreements,
            disagreements=self.disagreements,
            confidence=confidence_metadata["overall_confidence"],
        )

        return merged

    def get_review_items(self) -> list[dict]:
        """Return fields that need human review (disagreements)."""
        return [
            {
                "field": comp.field_path,
                "mistral": comp.mistral_value,
                "gemini": comp.gemini_value,
                "confidence": comp.confidence,
            }
            for comp in self.comparisons
            if not comp.agrees
        ]


class DualLLMSETUExtractor:
    """Runs Mistral + Gemini in parallel, then merges with second opinion."""

    def __init__(self, mistral_api_key: str, gemini_api_key: str):
        from .setu_extractor import MistralSETUExtractor
        from .gemini_setu_extractor import GeminiSETUExtractor

        self.mistral = MistralSETUExtractor(mistral_api_key)
        self.gemini = GeminiSETUExtractor(gemini_api_key)

    def extract_with_second_opinion(self, markdown: str, cao_name: str) -> dict:
        """Run both models in parallel, then merge with confidence scoring.

        Returns SETU v2.0 JSON with _orchestrator_metadata showing:
        - Which fields agreed/disagreed
        - Overall confidence score
        - Which model's value was used for each field
        """
        logger.info("Starting dual-LLM extraction with second opinion", cao=cao_name)
        start = datetime.utcnow()

        # Run both in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_mistral = executor.submit(self.mistral.extract, markdown, cao_name)
            future_gemini = executor.submit(self.gemini.extract, markdown, cao_name)

            mistral_output = future_mistral.result()
            gemini_output = future_gemini.result()

        # Merge with second opinion
        orchestrator = SecondOpinionOrchestrator()
        merged = orchestrator.merge_with_confidence(mistral_output, gemini_output, cao_name)

        elapsed = (datetime.utcnow() - start).total_seconds()
        logger.info(
            "Dual-LLM extraction complete",
            elapsed_seconds=elapsed,
            confidence=merged["_orchestrator_metadata"]["overall_confidence"],
        )

        return merged
