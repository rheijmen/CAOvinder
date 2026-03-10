"""
Schema Intelligence Layer

Analyzes official SETU v2.0.0-draft.3 schema and generates:
- Field-by-field extraction prompts
- Validation rules per field
- Examples from existing valid data
- Decision trees for ambiguous cases

This is the BRAIN that helps LLMs understand the SETU schema deeply.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


@dataclass
class FieldGuide:
    """Complete guide for extracting and validating a single SETU field"""

    field_path: str
    expected_type: str
    is_array: bool
    required_fields: list[str]
    allowed_properties: list[str]
    enum_values: list[str] | None
    structure: dict[str, Any]
    extraction_prompt: str
    examples: list[Any]


@dataclass
class ValidationResult:
    """Result of field validation"""

    is_valid: bool
    errors: list[dict[str, Any]]


@dataclass
class DecisionTree:
    """Decision tree for ambiguous data placement"""

    query: str
    recommended_field: str
    reasoning: str
    alternatives: list[str]


class SETUSchemaGuide:
    """
    Schema Intelligence Layer for SETU v2.0.0-draft.3

    Provides:
    1. Field-by-field extraction guidance
    2. Real-time validation
    3. Decision trees for ambiguous data
    4. Examples from valid CAOs
    """

    def __init__(self):
        # Load official SETU schema (134KB, 130 additionalProperties constraints)
        schema_path = Path(__file__).parent / "schemas" / "setu_v2.0.0-draft.3.json"
        with open(schema_path) as f:
            self.schema = json.load(f)

        # Load field mapping aliases (150+ aliases)
        field_mapping_path = Path(__file__).parent.parent.parent / ".claude" / "skills" / "llm-field-mapping.md"
        if field_mapping_path.exists():
            self.field_mappings = field_mapping_path.read_text()
        else:
            self.field_mappings = ""

        # Load valid examples (IKEA has 0 errors)
        self._load_valid_examples()

        # Build field guides
        self._build_field_guides()

    def _load_valid_examples(self):
        """Load examples from CAOs with 0 validation errors"""
        self.examples = {}

        # IKEA CAO has 0 errors - use as examples
        ikea_path = Path("data/setu/1049-ikea-cao-1-10-2023-tm-31-12-2024-v07022024.setu.json")
        if ikea_path.exists():
            with open(ikea_path) as f:
                ikea_data = json.load(f)
                self.examples["ikea"] = ikea_data

    def _build_field_guides(self):
        """Build field-by-field extraction guides"""
        self.field_guides: dict[str, FieldGuide] = {}

        # Get InquiryPayEquity properties
        inquiry_def = self.schema["$defs"]["InquiryPayEquity"]
        properties = inquiry_def.get("properties", {})

        # Build guides for root-level fields
        for field_name, field_schema in properties.items():
            guide = self._build_field_guide(field_name, field_schema)
            self.field_guides[field_name] = guide

    def _build_field_guide(self, field_name: str, field_schema: dict) -> FieldGuide:
        """Build extraction guide for a single field"""

        # Determine type
        field_type = field_schema.get("type", "unknown")
        is_array = field_type == "array"

        # Get items schema if array
        if is_array:
            items_schema = field_schema.get("items", {})
        else:
            items_schema = field_schema

        # Get required fields
        required_fields = items_schema.get("required", [])

        # Get allowed properties
        allowed_properties = list(items_schema.get("properties", {}).keys())

        # Get enum values
        enum_values = items_schema.get("enum", None)

        # Build structure example
        structure = self._build_structure_example(field_name, items_schema)

        # Build extraction prompt
        extraction_prompt = self._build_extraction_prompt(field_name, field_schema)

        # Get examples
        examples = self.get_examples_for_field(field_name)

        return FieldGuide(
            field_path=field_name,
            expected_type=field_type,
            is_array=is_array,
            required_fields=required_fields,
            allowed_properties=allowed_properties,
            enum_values=enum_values,
            structure=structure,
            extraction_prompt=extraction_prompt,
            examples=examples,
        )

    def _build_structure_example(self, field_name: str, schema: dict) -> dict:
        """Build structure example from schema"""

        # Special cases for common fields
        if field_name == "currency":
            return {
                "schemeAgencyId": "iso-4217",
                "value": "EUR"
            }
        elif field_name == "versionId":
            return {"value": "v27062024"}
        elif field_name == "holidayAllowance":
            return {
                "origin": {"type": "CollectiveLabourAgreement"},
                "line": [{"amount": {"baseAmount": {"value": 8.0}}}]
            }

        # Generic structure from schema
        properties = schema.get("properties", {})
        structure = {}
        for prop_name, prop_schema in properties.items():
            prop_type = prop_schema.get("type", "string")
            if prop_type == "string":
                structure[prop_name] = f"<{prop_name}>"
            elif prop_type == "number":
                structure[prop_name] = 0.0
            elif prop_type == "object":
                structure[prop_name] = {}
            elif prop_type == "array":
                structure[prop_name] = []

        return structure

    def _build_extraction_prompt(self, field_name: str, schema: dict) -> str:
        """Build extraction prompt for a field"""

        # Get description
        description = schema.get("description", "")

        # Special prompts for common fields
        if field_name == "currency":
            return """Extract the currency used for monetary amounts.

WHERE TO FIND:
- Salary tables (loonschalen) usually show currency
- Dutch CAOs almost always use EUR
- Look for "€", "EUR", or "euro"

STRUCTURE:
{
  "schemeAgencyId": "iso-4217",
  "value": "EUR"
}

IF UNCERTAIN:
- Default to EUR (99% of Dutch CAOs)
- Flag as "uncertain_currency_assumed_eur" """

        elif field_name == "versionId":
            return """Extract the version identifier of this document.

WHERE TO FIND:
- Header/footer showing version
- Publication/revision date
- Can derive from "versie" or date

STRUCTURE:
{"value": "v27062024"}

IF UNCERTAIN:
- Use publication date in format "vYYYYMMDD"
- Flag as "uncertain_versionId_from_date" """

        elif field_name == "holidayAllowance":
            return """Extract holiday allowance (vakantietoeslag) arrangement.

WHERE TO FIND:
- Section titled "Vakantietoeslag"
- Percentage (typically 8%)
- Payment date (usually May)

CRITICAL STRUCTURE:
{
  "origin": {"type": "CollectiveLabourAgreement"},
  "line": [
    {
      "amount": {
        "baseAmount": {"value": 8.0},
        "proportional": {"baseDefinition": "salary"}
      }
    }
  ],
  "payDate": {"month": 5}
}

REQUIRED: "origin" field must be present
NOT ALLOWED: "percentage", "description" as direct properties

IF UNCERTAIN:
- Flag specific ambiguous fields """

        # Generic prompt
        return f"""{description}

Extract this field from the CAO document.
Follow the official SETU v2.0.0-draft.3 schema exactly.

IF UNCERTAIN:
- Flag as "uncertain_{field_name}_<reason>" """

    def get_field_guide(self, field_path: str) -> FieldGuide | None:
        """Get extraction guide for a field"""
        return self.field_guides.get(field_path)

    def validate_field(self, field_path: str, value: Any) -> ValidationResult:
        """
        Validate a field value against official schema

        Returns ValidationResult with errors if any
        """
        # Create minimal document with just this field
        test_doc = {field_path: value}

        # Add required fields with minimal values
        if field_path != "documentId":
            test_doc["documentId"] = "test-doc-id"
        if field_path != "effectivePeriod":
            test_doc["effectivePeriod"] = {"start": "2024-01-01"}
        if field_path != "customer":
            test_doc["customer"] = {"id": "test-customer"}
        if field_path != "remuneration":
            test_doc["remuneration"] = [{}]

        # Validate
        validator = Draft202012Validator(self.schema)
        errors = []

        for error in validator.iter_errors(test_doc):
            # Only include errors related to our field
            if str(field_path) in "/".join(str(p) for p in error.path):
                errors.append({
                    "message": error.message,
                    "path": "/".join(str(p) for p in error.path),
                    "validator": error.validator,
                })

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )

    def get_examples_for_field(self, field_name: str) -> list[Any]:
        """Get examples from valid CAOs"""
        examples = []

        # Get from IKEA
        if "ikea" in self.examples:
            ikea_data = self.examples["ikea"]
            if field_name in ikea_data:
                examples.append(ikea_data[field_name])

        return examples

    def get_decision_tree(self, query: str) -> DecisionTree:
        """
        Get decision tree for ambiguous data placement

        E.g., "8% vakantietoeslag" could go in:
        - holidayAllowance[]  (if annual payment)
        - remuneration.allowance[]  (if per-period payment)
        """

        query_lower = query.lower()

        # Holiday allowance decision
        if "vakantietoeslag" in query_lower or "holiday allowance" in query_lower:
            return DecisionTree(
                query=query,
                recommended_field="holidayAllowance",
                reasoning="Holiday allowance (vakantietoeslag) is annual payment, goes in holidayAllowance[]",
                alternatives=["remuneration.allowance"]
            )

        # Shift/irregular allowances
        if any(word in query_lower for word in ["ploegen", "shift", "onregelmati", "irregular", "ort"]):
            return DecisionTree(
                query=query,
                recommended_field="remuneration.allowance",
                reasoning="Shift/irregular allowances are recurring, go in remuneration.allowance[]",
                alternatives=["holidayAllowance"]
            )

        # Default: needs review
        return DecisionTree(
            query=query,
            recommended_field="unknown",
            reasoning="Cannot determine placement automatically - needs human review",
            alternatives=[]
        )

    def build_guided_extraction_prompt(self) -> str:
        """
        Build complete guided extraction prompt with:
        - Field-by-field instructions
        - Structure examples
        - Uncertainty flagging
        - Decision trees
        """

        prompt_parts = []

        # Header
        prompt_parts.append("""You are extracting SETU v2.0 InquiryPayEquity data from a Dutch CAO.

CRITICAL RULES:
1. Follow official SETU v2.0.0-draft.3 schema EXACTLY
2. For EACH field below, follow the specific guidance
3. If ANY field is uncertain, flag it with "uncertain_<reason>"
4. Extract ALL occurrences (e.g., multiple salary scales = multiple array entries)
5. Preserve information accurately

FIELD-BY-FIELD GUIDANCE:
""")

        # Add guidance for each field
        for field_name, guide in self.field_guides.items():
            prompt_parts.append(f"\n## {field_name}")
            prompt_parts.append(f"Type: {guide.expected_type}")
            if guide.is_array:
                prompt_parts.append("(Array - each item is separate entry)")
            if guide.required_fields:
                prompt_parts.append(f"Required: {', '.join(guide.required_fields)}")

            prompt_parts.append(f"\n{guide.extraction_prompt}")

            if guide.examples:
                prompt_parts.append(f"\nExample:\n```json\n{json.dumps(guide.examples[0], indent=2)}\n```")

        # Footer with field mappings
        prompt_parts.append("\n\nFIELD MAPPING ALIASES (150+ Dutch terms):")
        prompt_parts.append(self.field_mappings[:2000])  # Include first 2000 chars

        prompt_parts.append("""

RETURN FORMAT:
{
  "setu_data": { /* complete SETU JSON */ },
  "uncertain_fields": [
    {"path": "field.path", "reason": "why_uncertain", "confidence": 0.8}
  ]
}
""")

        return "\n".join(prompt_parts)
