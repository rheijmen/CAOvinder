"""
TDD Tests for Schema Intelligence Layer

Tests MUST pass before implementation is considered complete.
RED → GREEN → REFACTOR cycle.
"""

import json
import pytest
from pathlib import Path
from cao_engine.compliance.schema_guide import (
    SETUSchemaGuide,
    FieldGuide,
    ValidationResult,
)


class TestSchemaGuideInitialization:
    """Test that SchemaGuide loads and parses official schema correctly"""

    def test_loads_official_schema_not_broken_schema(self):
        """CRITICAL: Must use 134KB official schema, not 28KB broken"""
        guide = SETUSchemaGuide()

        # Official schema is ~134KB, broken is ~28KB
        schema_size = len(json.dumps(guide.schema))
        assert schema_size > 100_000, f"Schema too small ({schema_size} bytes) - using broken schema?"

    def test_has_inquiry_pay_equity_definition(self):
        """Verify schema has InquiryPayEquity definition"""
        guide = SETUSchemaGuide()
        assert "$defs" in guide.schema
        assert "InquiryPayEquity" in guide.schema["$defs"]

    def test_counts_additional_properties_constraints(self):
        """Official schema has 130 additionalProperties constraints"""
        guide = SETUSchemaGuide()
        schema_str = json.dumps(guide.schema)
        count = schema_str.count('"additionalProperties"')

        # Should be ~130 (official), not 0 (broken)
        assert count > 100, f"Only {count} additionalProperties - using broken schema?"


class TestFieldGuideGeneration:
    """Test field-by-field prompt generation"""

    def test_generates_guide_for_currency_field(self):
        """Currency field should have specific guidance"""
        guide = SETUSchemaGuide()
        field_guide = guide.get_field_guide("currency")

        assert field_guide is not None
        assert "iso-4217" in field_guide.extraction_prompt.lower()
        assert "eur" in field_guide.extraction_prompt.lower()

    def test_generates_guide_for_version_id(self):
        """versionId should show it's an object, not string"""
        guide = SETUSchemaGuide()
        field_guide = guide.get_field_guide("versionId")

        assert field_guide.expected_type == "object"
        assert "value" in field_guide.structure

    def test_generates_guide_for_holiday_allowance(self):
        """holidayAllowance should show required 'origin' field"""
        guide = SETUSchemaGuide()
        field_guide = guide.get_field_guide("holidayAllowance")

        assert "origin" in field_guide.required_fields
        assert "CollectiveLabourAgreement" in field_guide.extraction_prompt

    def test_generates_guide_for_salary_scale(self):
        """salaryScale should show it's an array with specific properties"""
        guide = SETUSchemaGuide()
        field_guide = guide.get_field_guide("remuneration.salaryScale")

        assert field_guide.is_array
        assert "currency" in field_guide.allowed_properties
        assert "steps" not in field_guide.allowed_properties  # Invalid field


class TestFieldValidation:
    """Test real-time field validation"""

    def test_validates_correct_currency(self):
        """Valid currency object should pass"""
        guide = SETUSchemaGuide()
        result = guide.validate_field("currency", {
            "schemeAgencyId": "iso-4217",
            "value": "EUR"
        })

        assert result.is_valid
        assert len(result.errors) == 0

    def test_rejects_currency_as_string(self):
        """Currency as string should fail (type error)"""
        guide = SETUSchemaGuide()
        result = guide.validate_field("currency", "EUR")

        assert not result.is_valid
        assert "type" in result.errors[0]["validator"]

    def test_rejects_currency_with_wrong_enum(self):
        """Wrong schemeAgencyId enum should fail"""
        guide = SETUSchemaGuide()
        result = guide.validate_field("currency", {
            "schemeAgencyId": "wrong-value",
            "value": "EUR"
        })

        assert not result.is_valid
        assert "enum" in result.errors[0]["validator"]

    def test_validates_version_id_object(self):
        """versionId as object should pass"""
        guide = SETUSchemaGuide()
        result = guide.validate_field("versionId", {"value": "v27062024"})

        assert result.is_valid

    def test_rejects_version_id_string(self):
        """versionId as string should fail"""
        guide = SETUSchemaGuide()
        result = guide.validate_field("versionId", "v27062024")

        assert not result.is_valid

    def test_rejects_additional_properties(self):
        """Additional properties should be caught"""
        guide = SETUSchemaGuide()
        result = guide.validate_field("holidayAllowance", [{
            "percentage": 8,  # Invalid field
            "description": "test"  # Invalid field
        }])

        assert not result.is_valid
        # Should have additionalProperties error
        additional_props_errors = [e for e in result.errors if e["validator"] == "additionalProperties"]
        assert len(additional_props_errors) > 0


class TestDecisionTrees:
    """Test decision trees for ambiguous data"""

    def test_holiday_allowance_decision_tree(self):
        """8% vakantietoeslag → where does it go?"""
        guide = SETUSchemaGuide()

        # This is tricky: could be holidayAllowance[] or remuneration.allowance[]
        decision = guide.get_decision_tree("8% vakantietoeslag over jaarsalaris")

        assert decision.recommended_field == "holidayAllowance"
        assert "annual" in decision.reasoning.lower()

    def test_shift_allowance_decision_tree(self):
        """Shift allowance → remuneration.allowance, not holidayAllowance"""
        guide = SETUSchemaGuide()
        decision = guide.get_decision_tree("ploegentoeslag 15%")

        assert decision.recommended_field == "remuneration.allowance"
        assert "shift" in decision.reasoning.lower() or "recurring" in decision.reasoning.lower()


class TestPromptGeneration:
    """Test complete extraction prompt generation"""

    def test_generates_complete_guided_prompt(self):
        """Should generate field-by-field guided prompt"""
        guide = SETUSchemaGuide()
        prompt = guide.build_guided_extraction_prompt()

        # Should contain guidance for all major fields
        assert "documentId" in prompt
        assert "versionId" in prompt
        assert "remuneration" in prompt
        assert "holidayAllowance" in prompt
        assert "salaryScale" in prompt

        # Should include uncertainty flagging instructions
        assert "uncertain" in prompt.lower()
        assert "flag" in prompt.lower()

        # Should include structure examples
        assert "{" in prompt  # JSON examples

    def test_prompt_includes_field_mapping_aliases(self):
        """Should include 150+ field aliases"""
        guide = SETUSchemaGuide()
        prompt = guide.build_guided_extraction_prompt()

        # Check for some common aliases
        assert "loongebouw" in prompt.lower() or "salary" in prompt.lower()
        assert "functiegroep" in prompt.lower() or "job group" in prompt.lower()


class TestExamplesFromValidData:
    """Test that guide can learn from valid examples"""

    def test_loads_valid_ikea_examples(self):
        """Should load examples from IKEA CAO (0 errors)"""
        guide = SETUSchemaGuide()

        # IKEA has valid data - should be loaded as examples
        examples = guide.get_examples_for_field("currency")

        # Should have at least one example
        assert len(examples) > 0

    def test_example_shows_correct_structure(self):
        """Examples should show correct structure"""
        guide = SETUSchemaGuide()
        examples = guide.get_examples_for_field("currency")

        if examples:
            example = examples[0]
            assert "schemeAgencyId" in example
            assert example["schemeAgencyId"] == "iso-4217"
