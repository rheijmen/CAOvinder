"""
Complete CAO to SETU v2.0 Processing Pipeline
Converts any CAO JSON to fully compliant SETU v2.0 format.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any


def fix_document_id(data: dict[str, Any]) -> dict[str, Any]:
    """Fix documentId - schemeAgencyId must be Customer or Supplier."""
    doc_id = data.get("documentId", {})
    if isinstance(doc_id, str):
        return {"value": doc_id, "schemeAgencyId": "Customer"}

    scheme = doc_id.get("schemeAgencyId", "Customer")
    if scheme not in ["Customer", "Supplier"]:
        scheme = "Customer"

    return {"value": doc_id.get("value", ""), "schemeAgencyId": scheme}


def fix_customer(customer: dict[str, Any]) -> dict[str, Any]:
    """Fix customer - legalId schemeAgencyId must be KvK, OIN, or RSIN."""
    customer = customer.copy()

    if "legalId" in customer and isinstance(customer["legalId"], list):
        for legal_id in customer["legalId"]:
            if "schemeAgencyId" in legal_id:
                if legal_id["schemeAgencyId"] not in ["KvK", "OIN", "RSIN"]:
                    legal_id["schemeAgencyId"] = "KvK"

    if "personContacts" in customer and isinstance(customer["personContacts"], list):
        for contact in customer["personContacts"]:
            if "name" in contact and isinstance(contact["name"], str):
                contact["name"] = {"formattedName": contact["name"]}

    return customer


def fix_position_profiles(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fix positionProfile - only 5 allowed fields."""
    fixed = []
    for profile in profiles:
        clean = {}

        # REQUIRED fields
        if "positionId" in profile:
            if isinstance(profile["positionId"], str):
                clean["positionId"] = {"value": profile["positionId"]}
            else:
                clean["positionId"] = profile["positionId"]
        else:
            clean["positionId"] = {"value": profile.get("positionTitle", "UNKNOWN")}

        clean["positionTitle"] = profile.get("positionTitle", "Unknown")
        clean["origin"] = profile.get("origin", {"type": "CollectiveLabourAgreement"})

        # OPTIONAL fields
        if "referenceTitle" in profile:
            ref = profile["referenceTitle"]
            clean["referenceTitle"] = ref if isinstance(ref, str) else ref.get("value", "")
        if "workDescription" in profile:
            clean["workDescription"] = profile["workDescription"]

        fixed.append(clean)

    return fixed


def fix_work_duration(wd: Any) -> dict[str, Any]:
    """Fix workDuration to exact schema."""
    if isinstance(wd, dict):
        if "amount" in wd:
            hours = wd["amount"].get("value", 40) if isinstance(wd["amount"], dict) else wd["amount"]
        elif "value" in wd:
            hours = wd["value"]
        else:
            hours = 40
    elif isinstance(wd, (int, float)):
        hours = wd
    else:
        hours = 40

    return {
        "amount": {"value": hours, "unitCode": "Hour"},
        "interval": {"value": 1, "unitCode": "Week"},
        "valuePerWeek": hours
    }


def fix_interval(interval: Any) -> dict[str, Any]:
    """Fix interval to IntervalType object."""
    if isinstance(interval, dict):
        return {"value": interval.get("value", 1), "unitCode": interval.get("unitCode", "Month")}
    elif isinstance(interval, str):
        return {"value": 1, "unitCode": interval}
    else:
        return {"value": 1, "unitCode": "Month"}


def fix_salary_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fix salary steps to exact schema."""
    fixed = []
    for step in steps:
        clean = {}

        # REQUIRED: name
        if "zone" in step:
            clean["name"] = str(step["zone"])
        elif "name" in step:
            clean["name"] = str(step["name"])
        else:
            clean["name"] = str(len(fixed) + 1)

        # REQUIRED: value (must be number)
        value = step.get("amount", step.get("value", 0))

        # Handle WML percentages
        if isinstance(value, str):
            match = re.match(r'(\d+)%\s*WML', value)
            if match:
                percentage = int(match.group(1))
                clean["value"] = round(2000 * (percentage / 100), 2)
                clean["minimumWage"] = True
            else:
                try:
                    clean["value"] = float(value)
                except:
                    clean["value"] = 0
        else:
            clean["value"] = float(value) if value else 0

        # OPTIONAL fields
        if "minimumWage" in step and "minimumWage" not in clean:
            clean["minimumWage"] = step["minimumWage"]
        if "conditions" in step:
            clean["conditions"] = step["conditions"]

        fixed.append(clean)

    return fixed


def fix_salary_scales(scales: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fix salaryScale to exact schema."""
    fixed = []
    for scale in scales:
        clean = {
            "name": scale.get("name", "Unknown"),
            "currency": "EUR"
        }

        # Optional fields
        if "maxValue" in scale:
            clean["maxValue"] = scale["maxValue"]
        if "minValue" in scale:
            clean["minValue"] = scale["minValue"]
        if "careerLevel" in scale:
            clean["careerLevel"] = scale["careerLevel"]

        # Fix salaryStep
        steps_data = scale.get("steps", scale.get("salaryStep", []))
        if steps_data:
            clean["salaryStep"] = fix_salary_steps(steps_data)

        fixed.append(clean)

    return fixed


def fix_remuneration(remuneration: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fix remuneration to exact schema."""
    fixed = []
    for rem in remuneration:
        clean = {
            "origin": rem.get("origin", {"type": "CollectiveLabourAgreement"}),
            "workDuration": fix_work_duration(rem.get("workDuration")),
            "interval": fix_interval(rem.get("interval", "Month")),
            "salaryScale": fix_salary_scales(rem.get("salaryScale", []))
        }

        # Optional fields
        if "effectivePeriod" in rem:
            clean["effectivePeriod"] = rem["effectivePeriod"]
        for field in ["hourlyWageConversion", "individualSalaryIncrease",
                      "generalSalaryIncrease", "conditions"]:
            if field in rem:
                clean[field] = rem[field]

        fixed.append(clean)

    return fixed


def process_cao_to_setu_v2(input_file: Path, output_file: Path) -> Path:
    """Process CAO JSON to fully compliant SETU v2.0."""

    print(f"📖 Reading {input_file.name}")
    with open(input_file, encoding='utf-8') as f:
        data = json.load(f)

    print("🔧 Applying SETU v2.0 transformations...")

    result = {
        "documentId": fix_document_id(data),
        "effectivePeriod": data.get("effectivePeriod", {"validFrom": "2024-01-01", "validTo": "2024-12-31"}),
        "customer": fix_customer(data.get("customer", {})),
        "remuneration": fix_remuneration(data.get("remuneration", []))
    }

    # Optional fields
    if "versionId" in data:
        if isinstance(data["versionId"], str):
            result["versionId"] = {"value": data["versionId"]}
        else:
            result["versionId"] = data["versionId"]

    if "issued" in data:
        result["issued"] = data["issued"]

    if "baseDefinition" in data:
        result["baseDefinition"] = data["baseDefinition"]

    if "labourAgreements" in data:
        result["labourAgreements"] = data["labourAgreements"]

    if "positionProfile" in data:
        result["positionProfile"] = fix_position_profiles(data["positionProfile"])

    for field in ["allowance", "holidayAllowance", "sickPay", "leave",
                  "individualChoiceBudget", "pension", "sustainableEmployability",
                  "supplementaryArrangement", "otherArrangement"]:
        if field in data:
            result[field] = data[field]

    print(f"💾 Saving to {output_file.name}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("✅ Complete!")
    return output_file


if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_path = Path(sys.argv[1])
    else:
        input_path = Path("data/setu/1004-achmea-cao-01-12-2023-tm-31-08-2025-vbest27062024.setu.json")

    output_path = input_path.parent / f"{input_path.stem}-VALID.setu.json"
    process_cao_to_setu_v2(input_path, output_path)
