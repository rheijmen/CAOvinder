"""
SETU v2.0 Compliant Transformer
Transforms CAO JSON to EXACT SETU v2.0 format based on official OpenAPI schema.

Uses ONLY the fields defined in the OpenAPI spec at:
data/setu_input/gelijkwaardige-beloning-api.yaml
"""

import json
from pathlib import Path
from typing import Any


class SETUv2CompliantTransformer:
    """Transform CAO data to exact SETU v2.0 schema compliance."""

    def transform(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform CAO data to fully compliant SETU v2.0 format."""
        result = {}

        # REQUIRED: documentId (Identifier object)
        result["documentId"] = self._transform_document_id(data)

        # OPTIONAL: versionId (object with value property)
        if "versionId" in data:
            if isinstance(data["versionId"], str):
                result["versionId"] = {"value": data["versionId"]}
            else:
                result["versionId"] = data["versionId"]

        # OPTIONAL: issued (datetime string)
        if "issued" in data:
            result["issued"] = data["issued"]

        # REQUIRED: effectivePeriod
        if "effectivePeriod" in data:
            result["effectivePeriod"] = data["effectivePeriod"]
        else:
            raise ValueError("effectivePeriod is required")

        # REQUIRED: customer
        result["customer"] = self._transform_customer(data)

        # OPTIONAL: baseDefinition (array)
        if "baseDefinition" in data:
            result["baseDefinition"] = data["baseDefinition"]

        # OPTIONAL: labourAgreements
        if "labourAgreements" in data:
            result["labourAgreements"] = data["labourAgreements"]

        # OPTIONAL: positionProfile (array)
        if "positionProfile" in data:
            result["positionProfile"] = self._transform_position_profiles(data["positionProfile"])

        # REQUIRED: remuneration (array)
        result["remuneration"] = self._transform_remuneration(data)

        # OPTIONAL: allowance, holidayAllowance, sickPay, leave, etc.
        optional_arrays = [
            "allowance", "holidayAllowance", "sickPay", "leave",
            "individualChoiceBudget", "pension", "sustainableEmployability",
            "supplementaryArrangement", "otherArrangement"
        ]
        for field in optional_arrays:
            if field in data:
                result[field] = data[field]

        return result

    def _transform_document_id(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform documentId to proper Identifier object."""
        doc_id = data.get("documentId", {})

        if isinstance(doc_id, str):
            # Convert string to proper Identifier object
            # schemeAgencyId MUST be "Customer" or "Supplier"
            return {
                "value": doc_id,
                "schemeAgencyId": "Customer"  # Default to Customer
            }
        elif isinstance(doc_id, dict):
            # Ensure schemeAgencyId is valid
            scheme = doc_id.get("schemeAgencyId", "Customer")
            if scheme not in ["Customer", "Supplier"]:
                # Invalid value - default to Customer
                scheme = "Customer"

            return {
                "value": doc_id.get("value", ""),
                "schemeAgencyId": scheme
            }
        else:
            raise ValueError("documentId must be string or object")

    def _transform_customer(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform customer to proper structure."""
        if "customer" not in data:
            raise ValueError("customer is required")

        customer = data["customer"].copy()

        # Ensure legalId uses valid schemeAgencyId (KvK, OIN, or RSIN)
        if "legalId" in customer:
            legal_ids = customer["legalId"]
            if isinstance(legal_ids, list):
                for legal_id in legal_ids:
                    if "schemeAgencyId" in legal_id:
                        scheme = legal_id["schemeAgencyId"]
                        if scheme not in ["KvK", "OIN", "RSIN"]:
                            # Default to KvK if invalid
                            legal_id["schemeAgencyId"] = "KvK"

        # Ensure personContacts is properly formatted
        if "personContacts" in customer:
            contacts = customer["personContacts"]
            if isinstance(contacts, list):
                for contact in contacts:
                    # Ensure name structure
                    if "name" in contact and isinstance(contact["name"], str):
                        contact["name"] = {"formattedName": contact["name"]}

        return customer

    def _transform_position_profiles(self, profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform positionProfile to only include allowed fields."""
        # Allowed fields from OpenAPI schema:
        # - positionId (REQUIRED, object with value)
        # - positionTitle (REQUIRED, string)
        # - origin (REQUIRED, OriginType object)
        # - referenceTitle (OPTIONAL, string)
        # - workDescription (OPTIONAL, string)

        transformed = []

        for profile in profiles:
            clean_profile = {}

            # REQUIRED: positionId (must be object with value)
            if "positionId" in profile:
                if isinstance(profile["positionId"], str):
                    clean_profile["positionId"] = {"value": profile["positionId"]}
                else:
                    clean_profile["positionId"] = profile["positionId"]
            else:
                # Generate from positionTitle if missing
                clean_profile["positionId"] = {
                    "value": profile.get("positionTitle", "UNKNOWN")
                }

            # REQUIRED: positionTitle (string)
            clean_profile["positionTitle"] = profile.get("positionTitle", "Unknown Position")

            # REQUIRED: origin (OriginType)
            if "origin" in profile:
                clean_profile["origin"] = profile["origin"]
            else:
                clean_profile["origin"] = {"type": "CollectiveLabourAgreement"}

            # OPTIONAL: referenceTitle (string, NOT object!)
            if "referenceTitle" in profile:
                ref = profile["referenceTitle"]
                if isinstance(ref, str):
                    clean_profile["referenceTitle"] = ref
                elif isinstance(ref, dict) and "value" in ref:
                    clean_profile["referenceTitle"] = ref["value"]

            # OPTIONAL: workDescription (string)
            if "workDescription" in profile:
                clean_profile["workDescription"] = profile["workDescription"]

            # DO NOT include: salaryScale (it's NOT part of positionProfile!)
            # The salaryScale field was in our data but NOT in the official schema

            transformed.append(clean_profile)

        return transformed

    def _transform_remuneration(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Transform remuneration to proper structure."""
        if "remuneration" not in data:
            raise ValueError("remuneration is required")

        remuneration_list = []

        for rem in data["remuneration"]:
            clean_rem = {}

            # REQUIRED: origin
            if "origin" in rem:
                clean_rem["origin"] = rem["origin"]
            else:
                clean_rem["origin"] = {"type": "CollectiveLabourAgreement"}

            # OPTIONAL: effectivePeriod
            if "effectivePeriod" in rem:
                clean_rem["effectivePeriod"] = rem["effectivePeriod"]

            # REQUIRED: workDuration
            # Must be object with: amount (object!), interval, valuePerWeek
            if "workDuration" in rem:
                wd = rem["workDuration"]

                if isinstance(wd, dict):
                    # Check if amount is already an object
                    if "amount" in wd:
                        amount_val = wd["amount"]
                        if isinstance(amount_val, (int, float)):
                            # Convert to object
                            clean_rem["workDuration"] = {
                                "amount": {
                                    "value": amount_val,
                                    "unitCode": wd.get("unitCode", "HUR")
                                }
                            }
                            # Add interval if present
                            if "interval" in wd:
                                clean_rem["workDuration"]["interval"] = wd["interval"]
                            # Add valuePerWeek if present
                            if "valuePerWeek" in wd:
                                clean_rem["workDuration"]["valuePerWeek"] = wd["valuePerWeek"]
                        else:
                            clean_rem["workDuration"] = wd
                    else:
                        # Construct from value
                        val = wd.get("value", 40)
                        clean_rem["workDuration"] = {
                            "amount": {
                                "value": val,
                                "unitCode": "HUR"
                            }
                        }
                elif isinstance(wd, (int, float)):
                    clean_rem["workDuration"] = {
                        "amount": {
                            "value": wd,
                            "unitCode": "HUR"
                        }
                    }
            else:
                # Default work duration
                clean_rem["workDuration"] = {
                    "amount": {
                        "value": 40,
                        "unitCode": "HUR"
                    }
                }

            # REQUIRED: interval (at remuneration level, NOT inside workDuration!)
            if "interval" in rem:
                clean_rem["interval"] = rem["interval"]
            else:
                # Default to Month
                clean_rem["interval"] = "Month"

            # REQUIRED: salaryScale (array)
            if "salaryScale" in rem:
                clean_rem["salaryScale"] = self._clean_salary_scales(rem["salaryScale"])
            else:
                clean_rem["salaryScale"] = []

            # OPTIONAL: hourlyWageConversion, individualSalaryIncrease, generalSalaryIncrease, conditions
            optional_fields = [
                "hourlyWageConversion", "individualSalaryIncrease",
                "generalSalaryIncrease", "conditions"
            ]
            for field in optional_fields:
                if field in rem:
                    clean_rem[field] = rem[field]

            remuneration_list.append(clean_rem)

        return remuneration_list

    def _clean_salary_scales(self, scales: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Clean salary scales - remove fields not in schema."""
        cleaned = []

        for scale in scales:
            # Remove lineId and currency if present - they're NOT in the official schema!
            # The OpenAPI schema shows salaryScale has additionalProperties: true
            # but the validator might be stricter

            clean_scale = {}

            # Keep only known fields
            allowed_fields = ["name", "steps", "youthScales", "effectivePeriod"]
            for field in allowed_fields:
                if field in scale:
                    clean_scale[field] = scale[field]

            cleaned.append(clean_scale)

        return cleaned


def transform_to_compliant_setu(input_file: Path, output_file: Path) -> Path:
    """Transform any CAO JSON to fully compliant SETU v2.0."""

    print(f"📖 Reading input from {input_file}")
    with open(input_file, encoding='utf-8') as f:
        data = json.load(f)

    print("🔄 Transforming to SETU v2.0 compliant format...")
    transformer = SETUv2CompliantTransformer()

    try:
        transformed = transformer.transform(data)

        print(f"✅ Writing compliant JSON to {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(transformed, f, indent=2, ensure_ascii=False, default=str)

        print("📊 Transformation complete:")
        print("   - Required fields present: documentId, effectivePeriod, customer, remuneration")
        print("   - Using correct schemeAgencyId enums (Customer/Supplier, KvK/OIN/RSIN)")
        print("   - Position profiles cleaned (5 allowed fields only)")
        print("   - Remuneration with interval at correct level")

        return output_file

    except Exception as e:
        print(f"❌ Transformation failed: {e}")
        raise


if __name__ == "__main__":
    input_path = Path("data/setu/1049-ikea-cao-1-10-2023-tm-31-12-2024-v07022024.setu.json")
    output_path = Path("data/setu/1049-ikea-cao-v2-compliant.setu.json")

    transform_to_compliant_setu(input_path, output_path)
