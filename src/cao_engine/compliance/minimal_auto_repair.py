"""
MINIMAL AUTO-REPAIR - Proof of Concept

Fixes ONLY the top 3 error patterns from Achmea analysis:
1. Strip additionalProperties (16 patterns, ~50 instances)
2. Fix versionId type (1 pattern, ~5 instances)
3. Fix workDuration structure (3 patterns, ~15 instances)

NO FANCY STUFF. Just the absolute minimum to prove it works.
If this doesn't reduce errors by 50%+ → approach is BS.
"""

import json
from pathlib import Path
from typing import Any


class MinimalAutoRepair:
    """
    Minimal auto-repair that fixes ONLY what we KNOW we can fix.

    No guessing. No fancy logic. Just deterministic rules.
    """

    def __init__(self):
        self.fixes_applied: list[str] = []

        # Load official schema to know what fields are valid
        schema_path = Path(__file__).parent / "schemas" / "setu_v2.0.0-draft.3.json"
        with open(schema_path) as f:
            self.official_schema = json.load(f)


    def repair(self, data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        """
        Apply repairs based on ACTUAL error patterns found.

        Fixes:
        1. Root additionalProperties
        2. versionId type
        3. workDuration structure
        4. baseDefinition additionalProperties (description field)
        5. remuneration additionalProperties (allowances field)
        6. salaryScale missing currency
        7. interval type (string → object)
        8. schemeAgencyId enum (Achmea → Customer)
        9. unitCode enum (HUR → Hour)
        """
        self.fixes_applied = []
        repaired = json.loads(json.dumps(data))  # Deep copy

        # FIX 1: Strip root additionalProperties
        repaired = self._fix_root_additional_properties(repaired)

        # FIX 2: Fix versionId type
        if "versionId" in repaired and isinstance(repaired["versionId"], str):
            old = repaired["versionId"]
            repaired["versionId"] = {"value": old}
            self.fixes_applied.append(f"Fixed versionId: '{old}' → object")

        # FIX 3: Fix baseDefinition additionalProperties
        if "baseDefinition" in repaired:
            for idx, base_def in enumerate(repaired["baseDefinition"]):
                if "description" in base_def:
                    del base_def["description"]
                    self.fixes_applied.append(f"Removed baseDefinition[{idx}].description (additionalProperty)")

        # FIX 4-9: Fix remuneration issues
        if "remuneration" in repaired:
            for idx, rem in enumerate(repaired["remuneration"]):
                # FIX 4: Remove 'allowances' additionalProperty
                if "allowances" in rem:
                    del rem["allowances"]
                    self.fixes_applied.append(f"Removed remuneration[{idx}].allowances (additionalProperty)")

                # FIX 5: Fix workDuration
                if "workDuration" in rem:
                    rem["workDuration"] = self._fix_work_duration(rem["workDuration"], idx)

                # FIX 6: Fix interval type (string → object)
                if "interval" in rem and isinstance(rem["interval"], str):
                    old = rem["interval"]
                    rem["interval"] = {"value": 1, "unitCode": old}
                    self.fixes_applied.append(f"Fixed remuneration[{idx}].interval: '{old}' → object")

                # FIX 7: Add missing currency + remove additionalProperties from salaryScale
                if "salaryScale" in rem:
                    for scale_idx, scale in enumerate(rem["salaryScale"]):
                        # Add currency
                        if "currency" not in scale:
                            scale["currency"] = "EUR"
                            self.fixes_applied.append(f"Added currency=EUR to salaryScale[{scale_idx}]")

                        # FIX 10: Remove additionalProperties (steps, youthScales)
                        valid_scale_fields = {"name", "minValue", "maxValue", "currency", "salaryStep", "careerLevel", "positionProfileReference"}
                        extra_fields = set(scale.keys()) - valid_scale_fields
                        for extra_field in extra_fields:
                            del scale[extra_field]
                            self.fixes_applied.append(f"Removed salaryScale[{scale_idx}].{extra_field} (additionalProperty)")

                # FIX 8: Fix unitCode enum (HUR → Hour)
                if "workDuration" in rem and "amount" in rem["workDuration"]:
                    if "unitCode" in rem["workDuration"]["amount"]:
                        if rem["workDuration"]["amount"]["unitCode"] == "HUR":
                            rem["workDuration"]["amount"]["unitCode"] = "Hour"
                            self.fixes_applied.append("Fixed unitCode: HUR → Hour")

        # FIX 9: Fix schemeAgencyId enum
        if "documentId" in repaired and "schemeAgencyId" in repaired["documentId"]:
            if repaired["documentId"]["schemeAgencyId"] not in ["Customer", "Supplier"]:
                old = repaired["documentId"]["schemeAgencyId"]
                repaired["documentId"]["schemeAgencyId"] = "Customer"  # Default to Customer
                self.fixes_applied.append(f"Fixed schemeAgencyId: '{old}' → 'Customer'")

        # FIX 11: Fix holidayAllowance type (object → array)
        if "holidayAllowance" in repaired and isinstance(repaired["holidayAllowance"], dict):
            old_value = repaired["holidayAllowance"]
            repaired["holidayAllowance"] = [old_value]
            self.fixes_applied.append("Fixed holidayAllowance: object → array")

        # FIX 12: Fix pension type (object → array)
        if "pension" in repaired and isinstance(repaired["pension"], dict):
            old_value = repaired["pension"]
            repaired["pension"] = [old_value]
            self.fixes_applied.append("Fixed pension: object → array")

        return repaired, self.fixes_applied


    def _fix_root_additional_properties(self, data: dict[str, Any]) -> dict[str, Any]:
        """Strip fields not in official SETU schema at root level."""

        # Valid root properties from official schema
        valid_root = set(self.official_schema.get("properties", {}).keys())

        # Find extras
        current_keys = set(data.keys())
        extra_keys = current_keys - valid_root

        # Remove them
        for key in extra_keys:
            del data[key]
            self.fixes_applied.append(f"Removed root additionalProperty: '{key}'")

        return data


    def _fix_work_duration(self, work_duration: dict[str, Any], rem_idx: int) -> dict[str, Any]:
        """
        Fix workDuration structure.

        Common error: Fields are flat instead of nested in 'amount'

        Wrong:
        {
          "value": 40,
          "unitCode": "Hour"
        }

        Right:
        {
          "amount": {"value": 40, "unitCode": "Hour"},
          "interval": {"value": 1, "unitCode": "Week"},
          "valuePerWeek": 40
        }
        """

        # Check if already correct (has amount, interval, valuePerWeek)
        if all(k in work_duration for k in ["amount", "interval", "valuePerWeek"]):
            return work_duration  # Already correct

        # Check if it has flat structure (value, unitCode at top level)
        if "value" in work_duration and "unitCode" in work_duration:
            value = work_duration["value"]
            unit_code = work_duration["unitCode"]

            # Restructure correctly
            fixed = {
                "amount": {
                    "value": value,
                    "unitCode": unit_code
                },
                "interval": {
                    "value": 1,
                    "unitCode": "Week"
                },
                "valuePerWeek": value  # Assume value is already per week
            }

            self.fixes_applied.append(
                f"Fixed workDuration[{rem_idx}] structure: flat → nested with amount/interval/valuePerWeek"
            )
            return fixed

        # If we can't fix it, return as-is
        return work_duration


# ============================================================================
# STANDALONE TEST FUNCTION - Run this file directly to test
# ============================================================================

def test_minimal_repair():
    """Test the minimal repair on actual Achmea data."""
    from jsonschema import Draft202012Validator

    print("="*70)
    print("MINIMAL AUTO-REPAIR TEST")
    print("="*70)

    # Load Achmea data
    achmea_path = Path("data/setu/1004-achmea-cao-01-12-2023-tm-31-08-2025-vbest27062024.setu.json")
    with open(achmea_path) as f:
        original_data = json.load(f)

    # Count original errors
    schema_path = Path("src/cao_engine/compliance/schemas/setu_v2.0.0-draft.3.json")
    with open(schema_path) as f:
        schema = json.load(f)

    validator = Draft202012Validator(schema)
    original_errors = list(validator.iter_errors(original_data))

    print("\n📊 BEFORE REPAIR")
    print(f"   Errors: {len(original_errors)}")

    # Apply minimal repair
    repairer = MinimalAutoRepair()
    repaired_data, fixes = repairer.repair(original_data)

    print(f"\n🔧 REPAIRS APPLIED: {len(fixes)}")
    for fix in fixes[:10]:  # Show first 10
        print(f"   - {fix}")
    if len(fixes) > 10:
        print(f"   ... and {len(fixes) - 10} more")

    # Count errors after repair
    repaired_errors = list(validator.iter_errors(repaired_data))

    print("\n📊 AFTER REPAIR")
    print(f"   Errors: {len(repaired_errors)}")

    # Calculate improvement
    errors_fixed = len(original_errors) - len(repaired_errors)
    if len(original_errors) > 0:
        improvement_pct = (errors_fixed / len(original_errors)) * 100
    else:
        improvement_pct = 0

    print("\n✅ RESULT")
    print(f"   Errors fixed: {errors_fixed}")
    print(f"   Improvement: {improvement_pct:.1f}%")

    # SUCCESS CRITERIA
    if improvement_pct >= 50:
        print(f"\n🎉 SUCCESS! Exceeded 50% target ({improvement_pct:.1f}%)")
        print("   → Approach is PROVEN, continue with full implementation")
    elif improvement_pct >= 30:
        print(f"\n⚠️  PARTIAL SUCCESS ({improvement_pct:.1f}%)")
        print("   → Approach works but needs more patterns")
        print("   → Add more repair rules and test again")
    else:
        print(f"\n❌ FAILURE ({improvement_pct:.1f}% < 30%)")
        print("   → Minimal repair doesn't work")
        print("   → STOP and redesign approach")

    # Save repaired output for inspection
    output_path = Path("data/setu/1004-achmea-MINIMAL-REPAIR-TEST.setu.json")
    with open(output_path, 'w') as f:
        json.dump(repaired_data, f, indent=2)
    print(f"\n💾 Repaired output saved: {output_path}")

    return improvement_pct >= 50


if __name__ == "__main__":
    test_minimal_repair()
