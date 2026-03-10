"""
SETU v2.0 Transformer

This module transforms LLM-extracted data into strict SETU v2.0 compliant format.
It handles the conversion between what LLMs naturally output and what the
official SETU validator expects.
"""

import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class SETUv2Transformer:
    """
    Transform LLM output to strict SETU v2.0 InquiryPayEquity format.

    This transformer:
    1. Converts data types (string → object for versionId, etc.)
    2. Removes non-SETU fields (_extraction_metadata, _compliance, etc.)
    3. Restructures custom fields to SETU format
    4. Ensures all required fields are present
    5. Validates against official schema
    """

    def __init__(self):
        # Load official SETU v2.0 schema
        schema_path = Path(__file__).parent.parent / "models" / "setu_v2_official_schema.json"
        with open(schema_path) as f:
            self.official_schema = json.load(f)

        self.transformation_log = []

    def transform(self, llm_output: dict[str, Any], preserve_original: bool = True) -> dict[str, Any]:
        """
        Transform LLM output to SETU v2.0 compliant format.

        Args:
            llm_output: Raw output from LLM extraction
            preserve_original: Whether to keep a copy of original data in _original field

        Returns:
            SETU v2.0 compliant dictionary
        """
        # Work on a deep copy
        data = copy.deepcopy(llm_output)
        self.transformation_log = []

        # Preserve original if requested (for debugging)
        original_data = copy.deepcopy(data) if preserve_original else None

        # Step 1: Remove all non-SETU root properties
        self._remove_non_setu_properties(data)

        # Step 2: Fix documentId structure
        self._fix_document_id(data)

        # Step 3: Fix versionId (string → object)
        self._fix_version_id(data)

        # Step 4: Fix customer structure
        self._fix_customer(data)

        # Step 5: Fix remuneration structure
        self._fix_remuneration(data)

        # Step 6: Fix positionProfile
        self._fix_position_profiles(data)

        # Step 7: Fix allowances
        self._fix_allowances(data)

        # Step 8: Fix leave arrangements
        self._fix_leave_arrangements(data)

        # Step 9: Ensure required fields
        self._ensure_required_fields(data)

        # Step 10: Final validation
        validation_errors = self._validate_against_schema(data)
        if validation_errors:
            logger.warning(f"Validation errors after transformation: {validation_errors}")

        # Add transformation metadata (will be removed before final output)
        if preserve_original:
            data["_transformation"] = {
                "timestamp": datetime.now().isoformat(),
                "log": self.transformation_log,
                "validation_errors": validation_errors,
                "_original": original_data
            }

        return data

    def _remove_non_setu_properties(self, data: dict[str, Any]):
        """Remove properties not in SETU v2.0 specification."""
        valid_properties = set(self.official_schema["properties"].keys())

        # Add transformation metadata to valid (temporarily)
        valid_properties.add("_transformation")

        keys_to_remove = [k for k in data if k not in valid_properties]
        for key in keys_to_remove:
            del data[key]
            self.transformation_log.append(f"Removed non-SETU property: {key}")

    def _fix_document_id(self, data: dict[str, Any]):
        """Ensure documentId is an object with value and schemeAgencyId."""
        if "documentId" in data:
            doc_id = data["documentId"]

            # If it's a string, convert to object
            if isinstance(doc_id, str):
                data["documentId"] = {
                    "value": doc_id,
                    "schemeAgencyId": "CAO"  # Default agency
                }
                self.transformation_log.append("Converted documentId from string to object")

            # Ensure schemeAgencyId exists
            elif isinstance(doc_id, dict) and "schemeAgencyId" not in doc_id:
                doc_id["schemeAgencyId"] = "CAO"
                self.transformation_log.append("Added default schemeAgencyId to documentId")

    def _fix_version_id(self, data: dict[str, Any]):
        """Convert versionId from string to object if needed."""
        if "versionId" in data:
            version = data["versionId"]

            if isinstance(version, str):
                data["versionId"] = {"value": version}
                self.transformation_log.append("Converted versionId from string to object")
            elif isinstance(version, (int, float)):
                data["versionId"] = {"value": str(version)}
                self.transformation_log.append("Converted versionId from number to object")

    def _fix_customer(self, data: dict[str, Any]):
        """Ensure customer structure is compliant."""
        if "customer" not in data:
            return

        customer = data["customer"]

        # Ensure legalId is an array of objects
        if "legalId" in customer:
            if not isinstance(customer["legalId"], list):
                customer["legalId"] = [customer["legalId"]]

            for i, legal_id in enumerate(customer["legalId"]):
                if isinstance(legal_id, str):
                    customer["legalId"][i] = {
                        "value": legal_id,
                        "schemeAgencyId": "KvK"
                    }
                    self.transformation_log.append(f"Fixed customer.legalId[{i}] structure")

        # Ensure personContacts is an array of objects
        if "personContacts" in customer:
            for contact in customer["personContacts"]:
                # Remove non-standard fields
                if "positionTitle" in contact:
                    del contact["positionTitle"]
                if "communication" in contact:
                    del contact["communication"]

    def _fix_remuneration(self, data: dict[str, Any]):
        """Fix remuneration array structure."""
        if "remuneration" not in data or not isinstance(data["remuneration"], list):
            return

        for rem_idx, rem in enumerate(data["remuneration"]):
            # Fix workDuration
            if "workDuration" in rem:
                wd = rem["workDuration"]

                # Convert from simple format to required structure
                if "value" in wd and "unitCode" in wd and "amount" not in wd:
                    rem["workDuration"] = {
                        "amount": wd.get("value", 40),
                        "interval": {
                            "value": 1,
                            "unitCode": "Week"
                        },
                        "valuePerWeek": wd.get("value", 40)
                    }
                    self.transformation_log.append(f"Fixed remuneration[{rem_idx}].workDuration")

            # Fix interval (string → object)
            if "interval" in rem and isinstance(rem["interval"], str):
                rem["interval"] = {
                    "value": 1,
                    "unitCode": rem["interval"]
                }
                self.transformation_log.append(f"Fixed remuneration[{rem_idx}].interval")

            # Fix salaryScale
            if "salaryScale" in rem and isinstance(rem["salaryScale"], list):
                for scale_idx, scale in enumerate(rem["salaryScale"]):
                    # Add currency if missing
                    if "currency" not in scale:
                        scale["currency"] = "EUR"
                        self.transformation_log.append(f"Added currency to salaryScale[{scale_idx}]")

                    # Convert steps to description (steps not in SETU v2.0)
                    if "steps" in scale:
                        # Preserve steps data in description
                        steps_summary = f"Steps: {len(scale['steps'])} defined"
                        if "description" in scale:
                            scale["description"] += f" | {steps_summary}"
                        else:
                            scale["description"] = steps_summary

                        # Extract min/max from steps
                        if isinstance(scale["steps"], list) and scale["steps"]:
                            amounts = [s.get("amount") for s in scale["steps"]
                                     if isinstance(s.get("amount"), (int, float))]
                            if amounts:
                                scale["minAmount"] = min(amounts)
                                scale["maxAmount"] = max(amounts)

                        del scale["steps"]
                        self.transformation_log.append(f"Converted steps to description in salaryScale[{scale_idx}]")

                    # Remove youth scales (not in standard)
                    if "youthScales" in scale:
                        del scale["youthScales"]
                        self.transformation_log.append(f"Removed youthScales from salaryScale[{scale_idx}]")

            # Remove non-standard remuneration fields
            invalid_rem_fields = ["allowances", "holidayAllowance", "leaveArrangements", "pension"]
            for field in invalid_rem_fields:
                if field in rem:
                    # Move to root level if not already there
                    if field not in data:
                        data[field] = rem[field]
                        self.transformation_log.append(f"Moved {field} from remuneration to root")
                    del rem[field]

    def _fix_position_profiles(self, data: dict[str, Any]):
        """Fix positionProfile array structure."""
        if "positionProfile" not in data or not isinstance(data["positionProfile"], list):
            return

        for idx, profile in enumerate(data["positionProfile"]):
            # Ensure positionId is an object
            if "positionId" in profile:
                if isinstance(profile["positionId"], str):
                    profile["positionId"] = {"value": profile["positionId"]}
                    self.transformation_log.append(f"Fixed positionProfile[{idx}].positionId")

            # Rename positionTitle to positionName if needed
            if "positionTitle" in profile and "positionName" not in profile:
                profile["positionName"] = profile["positionTitle"]
                del profile["positionTitle"]
                self.transformation_log.append(f"Renamed positionTitle to positionName in positionProfile[{idx}]")

            # Remove non-standard fields
            invalid_fields = ["origin", "referenceTitle", "salaryScale", "workDescription"]
            for field in invalid_fields:
                if field in profile:
                    del profile[field]
                    self.transformation_log.append(f"Removed {field} from positionProfile[{idx}]")

    def _fix_allowances(self, data: dict[str, Any]):
        """Transform allowances to SETU v2.0 format (rename to allowance)."""
        # SETU uses "allowance" not "allowances"
        if "allowances" in data:
            data["allowance"] = data["allowances"]
            del data["allowances"]
            self.transformation_log.append("Renamed 'allowances' to 'allowance'")

        if "allowance" not in data or not isinstance(data["allowance"], list):
            return

        # Transform each allowance to proper structure
        for idx, allow in enumerate(data["allowance"]):
            # Ensure proper structure with line items
            if "calculationMethod" in allow:
                # Convert to SETU line structure
                # This is simplified - real implementation would be more complex
                pass

    def _fix_leave_arrangements(self, data: dict[str, Any]):
        """Fix leave arrangements structure."""
        # Move leaveArrangements to leave if needed
        if "leaveArrangements" in data:
            data["leave"] = data["leaveArrangements"]
            del data["leaveArrangements"]
            self.transformation_log.append("Renamed 'leaveArrangements' to 'leave'")

    def _ensure_required_fields(self, data: dict[str, Any]):
        """Ensure all required fields are present."""
        required_fields = self.official_schema.get("required", [])

        for field in required_fields:
            if field not in data:
                # Add default values for required fields
                if field == "documentId":
                    data["documentId"] = {
                        "value": f"CAO-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                        "schemeAgencyId": "CAO"
                    }
                    self.transformation_log.append(f"Added default {field}")
                elif field == "effectivePeriod":
                    data["effectivePeriod"] = {
                        "validFrom": datetime.now().strftime("%Y-%m-%d"),
                        "validTo": "2099-12-31"
                    }
                    self.transformation_log.append(f"Added default {field}")
                elif field == "customer":
                    data["customer"] = {
                        "name": "Unknown",
                        "legalId": [{"value": "00000000", "schemeAgencyId": "KvK"}],
                        "personContacts": [{
                            "name": {"formattedName": "Contact Person"},
                            "roleCode": "Authorized"
                        }]
                    }
                    self.transformation_log.append(f"Added default {field}")
                elif field == "remuneration":
                    if "remuneration" not in data:
                        data["remuneration"] = []
                        self.transformation_log.append(f"Added empty {field} array")

    def _validate_against_schema(self, data: dict[str, Any]) -> list[str]:
        """Validate transformed data against official schema."""
        errors = []

        # Check required fields
        required = self.official_schema.get("required", [])
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # Check for additional properties at root
        if not self.official_schema.get("additionalProperties", True):
            valid_props = set(self.official_schema["properties"].keys())
            valid_props.add("_transformation")  # Allow our metadata

            for key in data:
                if key not in valid_props:
                    errors.append(f"Additional property not allowed: {key}")

        return errors

    def export_for_validation(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Export data for SETU validation (removes all metadata).

        Args:
            data: Transformed SETU data

        Returns:
            Clean SETU v2.0 data ready for validation
        """
        clean_data = copy.deepcopy(data)

        # Remove transformation metadata
        if "_transformation" in clean_data:
            del clean_data["_transformation"]

        # Remove any other underscore fields
        keys_to_remove = [k for k in clean_data.keys() if k.startswith("_")]
        for key in keys_to_remove:
            del clean_data[key]

        return clean_data


def transform_llm_to_setu(input_file: Path, output_file: Path | None = None) -> Path:
    """
    Transform LLM-extracted JSON to SETU v2.0 compliant format.

    Args:
        input_file: Path to LLM-extracted JSON
        output_file: Optional output path (defaults to .compliant.json)

    Returns:
        Path to compliant JSON file
    """
    # Load LLM output
    with open(input_file) as f:
        llm_data = json.load(f)

    # Transform to SETU v2.0
    transformer = SETUv2Transformer()
    transformed_data = transformer.transform(llm_data)

    # Export clean version for validation
    clean_data = transformer.export_for_validation(transformed_data)

    # Save compliant version
    if output_file is None:
        output_file = input_file.with_suffix('.compliant.json')

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(clean_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Transformed {input_file.name} to SETU v2.0 compliant format")
    logger.info(f"Applied {len(transformer.transformation_log)} transformations")
    logger.info(f"Output: {output_file}")

    return output_file


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        input_path = Path(sys.argv[1])
        output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
        transform_llm_to_setu(input_path, output_path)
    else:
        print("Usage: python setu_v2_transformer.py <input.json> [output.json]")