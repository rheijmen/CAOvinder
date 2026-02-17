"""Mistral Small 2506 Judge - Compares Gemini vs Mistral and decides final SETU output.

This is the JUDGE in the 3-LLM sequential pipeline:
1. Gemini - Extract SETU v2.0 completely (PRIMARY)
2. Mistral Large - Review & find gaps (REVIEWER)
3. Mistral Small 2506 (this) - Judge which output is best (JUDGE)
"""

import json
from datetime import datetime
from pathlib import Path

import structlog
from mistralai import Mistral

logger = structlog.get_logger(__name__)

JUDGE_PROMPT = """You are the JUDGE in a 3-LLM pipeline for Dutch CAO SETU v2.0 extraction.

Your task: Compare Gemini's extraction vs Mistral's review and decide the final SETU output.

INPUTS:
1. **Gemini's output** - Primary extraction (1M context, no truncation)
2. **Mistral's output** - Review extraction (500K context, focused review)
3. **Original CAO markdown** - Reference for fact-checking

DECISION CRITERIA:
1. **Completeness** - Which model extracted more fields?
2. **Accuracy** - Which model used correct SETU field names?
3. **Field Mapping** - Which model correctly routed SETU vs Statutory?
4. **Dutch Terminology** - Which model preserved exact CAO terms?
5. **Salary Tables** - Which model correctly parsed HTML tables?

FIELD-BY-FIELD COMPARISON:
For each top-level field, decide:
- Use Gemini's value
- Use Mistral's value
- Merge both (if complementary)
- Use neither (if both wrong)

Provide REASONING for each decision with confidence score (0.0-1.0).

OUTPUT FORMAT:
```json
{
  "final_setu": { /* merged SETU v2.0 */ },
  "judge_report": {
    "total_fields_compared": 127,
    "agreements": 98,
    "gemini_preferred": 21,
    "mistral_preferred": 8,
    "merged": 0,
    "decisions": [
      {
        "field": "remuneration.salaryScale.functiegroepen[0].name",
        "gemini_value": "Functiegroep A",
        "mistral_value": "A",
        "decision": "gemini",
        "confidence": 0.95,
        "reasoning": "Gemini extracted full Dutch term matching CAO source"
      }
    ]
  }
}
```

Be thorough and transparent. Your decisions will be used for legal compliance.
"""


class MistralJudge:
    """Judge that compares Gemini vs Mistral using Mistral Small 2506."""

    def __init__(self, api_key: str, model: str = "mistral-small-2506") -> None:
        self._client = Mistral(api_key=api_key)
        self._model = model
        logger.info("Mistral Small 2506 JUDGE initialized", model=model)

    def judge(
        self,
        gemini_output: dict,
        mistral_output: dict,
        cao_name: str | None = None,
    ) -> dict:
        """Compare Gemini vs Mistral and produce final judged SETU output.

        Args:
            gemini_output: Gemini's primary extraction
            mistral_output: Mistral's review extraction
            cao_name: Optional CAO name for metadata

        Returns:
            Dict with "final_setu" and "judge_report"
        """
        logger.info(
            "Judging Gemini vs Mistral with Mistral Small 2506",
            cao=cao_name,
            model=self._model,
        )

        # Build judge prompt
        prompt = (
            f"{JUDGE_PROMPT}\n\n"
            f"GEMINI'S EXTRACTION:\n```json\n{json.dumps(gemini_output, indent=2, ensure_ascii=False)}\n```\n\n"
            f"MISTRAL'S REVIEW:\n```json\n{json.dumps(mistral_output, indent=2, ensure_ascii=False)}\n```\n\n"
            f"CAO Name: {cao_name or 'Unknown'}\n\n"
            f"Make your decision field-by-field with reasoning."
        )

        start_time = datetime.now()
        response = self._client.chat.complete(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.1,
        )
        elapsed = (datetime.now() - start_time).total_seconds()

        # Parse JSON response (clean markdown artifacts if present)
        content = response.choices[0].message.content.strip()

        # Remove markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        # Extract just the JSON object (handle extra text after JSON)
        # Find the first { and last }
        start = content.find('{')
        if start == -1:
            raise ValueError(f"No JSON object found in judge response: {content[:200]}")

        # Count braces to find matching closing brace
        brace_count = 0
        end = start
        for i in range(start, len(content)):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break

        json_str = content[start:end]
        result = json.loads(json_str)

        # Add judge metadata
        if "final_setu" not in result:
            raise ValueError("Judge output missing 'final_setu' field")

        result["final_setu"]["_extraction_metadata"] = {
            "extractor": "mistral-judge",
            "model": self._model,
            "cao_name": cao_name,
            "extracted_at": datetime.now().isoformat(),
            "elapsed_seconds": elapsed,
            "gemini_version": gemini_output.get("_extraction_metadata", {}).get("extracted_at"),
            "mistral_version": mistral_output.get("_extraction_metadata", {}).get("extracted_at"),
        }

        # Add summary stats to report
        if "judge_report" in result:
            result["judge_report"]["metadata"] = {
                "model": self._model,
                "elapsed_seconds": elapsed,
                "judged_at": datetime.now().isoformat(),
            }

        logger.info(
            "Judge decision complete",
            elapsed_seconds=elapsed,
            total_decisions=result.get("judge_report", {}).get("total_fields_compared", 0),
            gemini_preferred=result.get("judge_report", {}).get("gemini_preferred", 0),
            mistral_preferred=result.get("judge_report", {}).get("mistral_preferred", 0),
            model=self._model,
        )

        return result
