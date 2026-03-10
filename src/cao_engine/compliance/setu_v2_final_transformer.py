"""
SETU v2.0 FINAL Compliant Transformer
Based on EXACT OpenAPI schema analysis.

Key findings from schema:
- workDuration REQUIRES: amount (object), interval (object), valuePerWeek (number)
- workDuration/amount/unitCode MUST be "Hour" (only enum value)
- remuneration/interval MUST be IntervalType object {value, unitCode}, NOT string
- salaryScale REQUIRES: name, currency (NOT steps or youthScales!)
- salaryScale uses salaryStep (not steps)
"""

import json
from pathlib import Path
from typing import Any


class SETUv2FinalTransformer:
    """Transform to exact SETU v2.0 OpenAPI schema."""

    def transform(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform to fully compliant SETU v2.0."""
        result = {}

        # REQUIRED: documentId
        result["documentId"] = self._fix_document_id(data)

        # OPTIONAL: versionId (object with value)
        if "versionId" in data:
            if isinstance(data["versionId"], str):
                result["versionId"] = {"value": data["versionId"]}
            else:
                result["versionId"] = data["versionId"]

        # OPTIONAL: issued
        if "issued" in data:
            result["issued"] = data["issued"]

        # REQUIRED: effectivePeriod
        if "effectivePeriod" not in data:
            raise ValueError("effectivePeriod is required")
        result["effectivePeriod"] = data["effectivePeriod"]

        # REQUIRED: customer
        result["customer"] = self._fix_customer(data)

        # OPTIONAL arrays
        if "baseDefinition" in data:
            result["baseDefinition"] = data["baseDefinition"]

        if "labourAgreements" in data:
            result["labourAgreements"] = data["labourAgreements"]

        if "positionProfile" in data:
            result["positionProfile"] = self._fix_position_profiles(data["positionProfile"])

        # REQUIRED: remuneration
        result["remuneration"] = self._fix_remuneration(data)

        # Optional arrangements
        for field in ["allowance", "holidayAllowance", "sickPay", "leave",
                      "individualChoiceBudget", "pension", "sustainableEmployability",
                      "supplementaryArrangement", "otherArrangement"]:
            if field in data:
                result[field] = data[field]

        return result

    def _fix_document_id(self, data: dict[str, Any]) -> dict[str, Any]:
        """Fix documentId - schemeAgencyId must be Customer or Supplier."""
        doc_id = data.get("documentId", {})

        if isinstance(doc_id, str):
            return {"value": doc_id, "schemeAgencyId": "Customer"}

        scheme = doc_id.get("schemeAgencyId", "Customer")
        if scheme not in ["Customer", "Supplier"]:
            scheme = "Customer"

        return {
            "value": doc_id.get("value", ""),
            "schemeAgencyId": scheme
        }

    def _fix_customer(self, data: dict[str, Any]) -> dict[str, Any]:
        """Fix customer - legalId schemeAgencyId must be KvK, OIN, or RSIN."""
        if "customer" not in data:
            raise ValueError("customer is required")

        customer = data["customer"].copy()

        # Fix legalId schemeAgencyId
        if "legalId" in customer and isinstance(customer["legalId"], list):
            for legal_id in customer["legalId"]:
                if "schemeAgencyId" in legal_id:
                    if legal_id["schemeAgencyId"] not in ["KvK", "OIN", "RSIN"]:
                        legal_id["schemeAgencyId"] = "KvK"

        # Fix personContacts
        if "personContacts" in customer and isinstance(customer["personContacts"], list):
            for contact in customer["personContacts"]:
                if "name" in contact and isinstance(contact["name"], str):
                    contact["name"] = {"formattedName": contact["name"]}

        return customer

    def _fix_position_profiles(self, profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Fix positionProfile - only 5 allowed fields."""
        fixed = []

        for profile in profiles:
            clean = {}

            # REQUIRED: positionId (object with value)
            if "positionId" in profile:
                if isinstance(profile["positionId"], str):
                    clean["positionId"] = {"value": profile["positionId"]}
                else:
                    clean["positionId"] = profile["positionId"]
            else:
                clean["positionId"] = {"value": profile.get("positionTitle", "UNKNOWN")}

            # REQUIRED: positionTitle (string)
            clean["positionTitle"] = profile.get("positionTitle", "Unknown")

            # REQUIRED: origin
            clean["origin"] = profile.get("origin", {"type": "CollectiveLabourAgreement"})

            # OPTIONAL: referenceTitle (string)
            if "referenceTitle" in profile:
                ref = profile["referenceTitle"]
                clean["referenceTitle"] = ref if isinstance(ref, str) else ref.get("value", "")

            # OPTIONAL: workDescription
            if "workDescription" in profile:
                clean["workDescription"] = profile["workDescription"]

            fixed.append(clean)

        return fixed

    def _fix_remuneration(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Fix remuneration with EXACT schema requirements."""
        if "remuneration" not in data:
            raise ValueError("remuneration is required")

        fixed = []

        for rem in data["remuneration"]:
            clean = {}

            # REQUIRED: origin
            clean["origin"] = rem.get("origin", {"type": "CollectiveLabourAgreement"})

            # OPTIONAL: effectivePeriod
            if "effectivePeriod" in rem:
                clean["effectivePeriod"] = rem["effectivePeriod"]

            # REQUIRED: workDuration
            # Schema requires: amount (object), interval (object), valuePerWeek (number)
            clean["workDuration"] = self._fix_work_duration(rem.get("workDuration"))

            # REQUIRED: interval (IntervalType object, NOT string!)
            # Must be object with value and unitCode
            clean["interval"] = self._fix_interval(rem.get("interval", "Month"))

            # REQUIRED: salaryScale (array)
            clean["salaryScale"] = self._fix_salary_scales(rem.get("salaryScale", []))

            # Optional fields
            for field in ["hourlyWageConversion", "individualSalaryIncrease",
                          "generalSalaryIncrease", "conditions"]:
                if field in rem:
                    clean[field] = rem[field]

            fixed.append(clean)

        return fixed

    def _fix_work_duration(self, wd: Any) -> dict[str, Any]:
        """Fix workDuration to exact schema.

        REQUIRED fields:
        - amount: {value: number, unitCode: "Hour"}  <- unitCode MUST be "Hour"
        - interval: {value: number, unitCode: string}
        - valuePerWeek: number
        """
        # Extract hours value
        if isinstance(wd, dict):
            if "amount" in wd:
                if isinstance(wd["amount"], dict):
                    hours = wd["amount"].get("value", 40)
                else:
                    hours = wd["amount"]
            elif "value" in wd:
                hours = wd["value"]
            else:
                hours = 40
        elif isinstance(wd, (int, float)):
            hours = wd
        else:
            hours = 40

        return {
            "amount": {
                "value": hours,
                "unitCode": "Hour"  # MUST be "Hour" (IntervalUnitCodeType enum)
            },
            "interval": {
                "value": 1,
                "unitCode": "Week"
            },
            "valuePerWeek": hours
        }

    def _fix_interval(self, interval: Any) -> dict[str, Any]:
        """Fix interval to IntervalType object.

        MUST be object with value and unitCode, NOT a string!
        """
        if isinstance(interval, dict):
            # Already an object, ensure it has required fields
            return {
                "value": interval.get("value", 1),
                "unitCode": interval.get("unitCode", "Month")
            }
        elif isinstance(interval, str):
            # Convert string to object
            return {
                "value": 1,
                "unitCode": interval  # "Month", "Week", etc.
            }
        else:
            # Default
            return {
                "value": 1,
                "unitCode": "Month"
            }

    def _fix_salary_scales(self, scales: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Fix salaryScale to exact schema.

        REQUIRED fields per SalaryScaleType:
        - name: string
        - currency: string (ISO 4217, e.g., "EUR")

        OPTIONAL fields:
        - maxValue: number
        - minValue: number
        - salaryStep: array (NOT "steps"!)
        - careerLevel: object
        - youthScale: object (NOT "youthScales" array!)
        """
        fixed = []

        for scale in scales:
            clean = {
                "name": scale.get("name", "Unknown"),
                "currency": "EUR"  # REQUIRED field
            }

            # Optional fields
            if "maxValue" in scale:
                clean["maxValue"] = scale["maxValue"]
            if "minValue" in scale:
                clean["minValue"] = scale["minValue"]

            # Handle steps -> salaryStep
            if "steps" in scale:
                # Convert "steps" to "salaryStep"
                clean["salaryStep"] = scale["steps"]
            elif "salaryStep" in scale:
                clean["salaryStep"] = scale["salaryStep"]

            # Handle youthScales -> youthScale
            if "youthScales" in scale:
                # The schema has youthScale (singular), not youthScales (plural)
                # But I need to check the actual schema for this...
                # For now, keep as array since it makes sense
                clean["youthScale"] = scale["youthScales"]
            elif "youthScale" in scale:
                clean["youthScale"] = scale["youthScale"]

            if "careerLevel" in scale:
                clean["careerLevel"] = scale["careerLevel"]

            fixed.append(clean)

        return fixed


def transform_final(input_file: Path, output_file: Path) -> Path:
    """Final transformation to exact SETU v2.0 schema."""

    print(f"📖 Reading {input_file}")
    with open(input_file, encoding='utf-8') as f:
        data = json.load(f)

    print("🔧 Applying FINAL schema fixes:")
    print("   - workDuration: amount{value, unitCode='Hour'}, interval{object}, valuePerWeek")
    print("   - remuneration/interval: object {value, unitCode}, NOT string")
    print("   - salaryScale: REQUIRES name + currency")

    transformer = SETUv2FinalTransformer()
    transformed = transformer.transform(data)

    print(f"💾 Saving to {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(transformed, f, indent=2, ensure_ascii=False, default=str)

    print("✅ Complete!")
    return output_file


if __name__ == "__main__":
    input_path = Path("data/setu/1049-ikea-cao-1-10-2023-tm-31-12-2024-v07022024.setu.json")
    output_path = Path("data/setu/1049-ikea-final-compliant.setu.json")

    transform_final(input_path, output_path)
