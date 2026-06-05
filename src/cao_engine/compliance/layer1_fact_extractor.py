"""
Layer 1: Fact Extractor
=======================
Extract ALL facts from CAO documents without schema constraints.
Focus on complete information capture, not structure.

This is the FIRST layer in our 4-layer compliance system.
"""

import json
from pathlib import Path
from typing import Any

import structlog
from mistralai import Mistral

logger = structlog.get_logger(__name__)


FACT_EXTRACTION_PROMPT = """You are extracting FACTS from a Dutch CAO document.

GOAL: Capture ALL information, don't worry about structure.

Extract these facts:
1. Document info (name, version, dates, parties)
2. Salary information (all scales, amounts, steps)
3. Allowances (holiday allowance %, year-end bonus, shift allowances)
4. Leave (vacation days, ADV, special leave)
5. Pension (fund name, percentages, franchise)
6. Working hours (standard week, overtime rules)
7. Any dates/moments when things change

Return as simple JSON with the facts you find. Examples:

{
  "document": {
    "name": "CAO Achmea",
    "version": "27-06-2024",
    "valid_from": "2023-12-01",
    "valid_until": "2025-08-31"
  },
  "holiday_allowance": {
    "percentage": 8,
    "payment_month": "May",
    "description": "8% of annual salary"
  },
  "salary_scales": [
    {
      "group": "A",
      "min": 2500,
      "max": 3500,
      "steps": [2500, 2600, 2700, ...]
    }
  ],
  "pension": {
    "fund_name": "SPA",
    "employer_percentage": 37.4,
    "employee_percentage": 3.25
  },
  ...
}

IMPORTANT: Extract EVERYTHING you see. We'll structure it later.
"""


class FactExtractor:
    """
    Layer 1: Extract facts from CAO without structural constraints.

    Goal: 100% information capture
    Output: Unstructured but complete JSON
    """

    def __init__(self, api_key: str):
        self.client = Mistral(api_key=api_key)
        self.model = "mistral-large-latest"

    def extract_facts(self, cao_text: str, cao_name: str) -> dict[str, Any]:
        """
        Extract ALL facts from CAO text.

        No schema constraints - just get the information.
        """
        logger.info("Extracting facts from CAO", cao=cao_name, text_length=len(cao_text))

        # Mistral Large has 128K token context (~400-500K characters)
        # Only truncate if absolutely necessary
        max_chars = 400_000
        if len(cao_text) > max_chars:
            cao_text = cao_text[:max_chars]
            logger.warning("Text truncated to fit context", original=len(cao_text), truncated=max_chars)
        else:
            logger.info("Processing full document", chars=len(cao_text))

        response = self.client.chat.complete(
            model=self.model,
            messages=[
                {"role": "system", "content": FACT_EXTRACTION_PROMPT},
                {
                    "role": "user",
                    "content": f"CAO: {cao_name}\n\nExtract ALL facts from this CAO:\n\n{cao_text}"
                }
            ],
            response_format={"type": "json_object"}
        )

        facts = json.loads(response.choices[0].message.content)

        # Log what we found
        logger.info(
            "Facts extracted",
            cao=cao_name,
            fact_count=len(facts),
            has_salary=("salary_scales" in facts),
            has_holiday=("holiday_allowance" in facts),
            has_pension=("pension" in facts)
        )

        return facts

    def extract_from_file(self, ocr_path: Path, cao_name: str) -> dict[str, Any]:
        """Extract facts from OCR markdown file."""
        cao_text = ocr_path.read_text(encoding="utf-8")
        return self.extract_facts(cao_text, cao_name)