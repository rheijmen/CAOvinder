"""
SETU v2.0 March 2026 Transformer
Transforms CAO JSON to fully compliant SETU v2.0 format with all March 2026 features.

Key v2.0 features implemented:
1. baseDefinition blocks for base salary calculations
2. supplementaryArrangement for RVU/generation pacts
3. lineId for cross-referencing between components
4. proportional indicators for pro-rata calculations
5. Individual leaveDayValue per leave type
6. WAZO leave support
7. Enhanced reference structures
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class SETUv2March2026Transformer:
    """Transform CAO data to SETU v2.0 March 2026 compliant format."""

    def __init__(self):
        self.line_id_counter = 1000
        self.line_references = {}  # Track line IDs for cross-referencing

    def generate_line_id(self, component_type: str, name: str = "") -> str:
        """Generate unique line ID for cross-referencing."""
        line_id = f"LINE-{component_type.upper()}-{self.line_id_counter:04d}"
        if name:
            line_id += f"-{name.replace(' ', '_').upper()}"
        self.line_id_counter += 1
        return line_id

    def transform(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform CAO data to March 2026 SETU v2.0 format."""
        result = {}

        # Core document fields
        self._transform_document_metadata(data, result)

        # Add baseDefinition if not present
        if "baseDefinition" not in data:
            result["baseDefinition"] = self._create_base_definition()
        else:
            result["baseDefinition"] = data["baseDefinition"]

        # Customer information
        self._transform_customer(data, result)

        # Labour agreements
        if "labourAgreements" in data:
            result["labourAgreements"] = data["labourAgreements"]

        # Position profiles with enhanced structure
        self._transform_position_profiles(data, result)

        # Remuneration with lineId support
        self._transform_remuneration(data, result)

        # Leave arrangements with individual leaveDayValue
        self._transform_leave(data, result)

        # Allowances with proportional indicators
        self._transform_allowances(data, result)

        # IKB with references
        self._transform_ikb(data, result)

        # Pension
        if "pension" in data:
            result["pension"] = self._enhance_pension(data["pension"])

        # Sustainable employability
        if "sustainableEmployability" in data:
            result["sustainableEmployability"] = data["sustainableEmployability"]

        # Add supplementaryArrangement if applicable
        self._add_supplementary_arrangement(data, result)

        # Other arrangements
        if "otherArrangement" in data:
            result["otherArrangement"] = data["otherArrangement"]

        return result

    def _transform_document_metadata(self, data: dict[str, Any], result: dict[str, Any]):
        """Transform document metadata to v2.0 format."""
        # Document ID
        if "documentId" in data:
            if isinstance(data["documentId"], dict):
                result["documentId"] = data["documentId"]
            else:
                result["documentId"] = {
                    "value": str(data["documentId"]),
                    "schemeAgencyId": "CAO"
                }

        # Version ID - must be an object in v2.0
        if "versionId" in data:
            if isinstance(data["versionId"], str):
                result["versionId"] = {"value": data["versionId"]}
            else:
                result["versionId"] = data["versionId"]
        else:
            result["versionId"] = {"value": "2.0"}

        # Issued date
        if "issued" in data:
            result["issued"] = data["issued"]
        else:
            result["issued"] = datetime.now().isoformat()

        # Effective period
        if "effectivePeriod" in data:
            result["effectivePeriod"] = data["effectivePeriod"]

    def _create_base_definition(self) -> list[dict[str, Any]]:
        """Create default baseDefinition for v2.0."""
        return [
            {
                "baseType": "BaseSalary",
                "remunerationIndicator": True,
                "holidayAllowanceIndicator": True,
                "paidLeaveDayIndicator": True,
                "allAllowancesIndicator": False,
                "description": "Base salary definition including holiday allowance and paid leave"
            }
        ]

    def _transform_customer(self, data: dict[str, Any], result: dict[str, Any]):
        """Transform customer information."""
        if "customer" in data:
            customer = data["customer"].copy()

            # Ensure personContacts is properly structured
            if "personContacts" in customer:
                contacts = customer["personContacts"]
                if isinstance(contacts, list) and contacts:
                    for contact in contacts:
                        # Fix name structure if needed
                        if "name" in contact:
                            if isinstance(contact["name"], str):
                                contact["name"] = {"formattedName": contact["name"]}
                        # Ensure roleCode exists
                        if "roleCode" not in contact:
                            contact["roleCode"] = "HR Contact"

            result["customer"] = customer

    def _transform_position_profiles(self, data: dict[str, Any], result: dict[str, Any]):
        """Transform position profiles with v2.0 enhancements."""
        if "positionProfile" in data:
            profiles = []
            for profile in data["positionProfile"]:
                enhanced_profile = profile.copy()

                # Add lineId for cross-referencing
                if "positionId" not in enhanced_profile:
                    enhanced_profile["positionId"] = {
                        "value": self.generate_line_id("POS", profile.get("positionName", ""))
                    }
                elif isinstance(enhanced_profile["positionId"], str):
                    enhanced_profile["positionId"] = {"value": enhanced_profile["positionId"]}

                profiles.append(enhanced_profile)

            result["positionProfile"] = profiles

    def _transform_remuneration(self, data: dict[str, Any], result: dict[str, Any]):
        """Transform remuneration with lineId and enhanced structure."""
        if "remuneration" not in data:
            return

        remuneration_list = []

        for rem in data["remuneration"]:
            enhanced_rem = {}

            # Copy basic fields
            if "origin" in rem:
                enhanced_rem["origin"] = rem["origin"]

            # Work duration with proper structure
            if "workDuration" in rem:
                wd = rem["workDuration"]
                if isinstance(wd, dict):
                    enhanced_rem["workDuration"] = {
                        "amount": wd.get("value", wd.get("amount", 36)),
                        "interval": {
                            "value": 1,
                            "unitCode": "Week"
                        },
                        "valuePerWeek": wd.get("value", wd.get("amount", 36))
                    }
                else:
                    enhanced_rem["workDuration"] = {
                        "amount": wd,
                        "interval": {"value": 1, "unitCode": "Week"},
                        "valuePerWeek": wd
                    }

            # Salary scales with enhanced structure
            if "salaryScale" in rem:
                scales = []
                for scale in rem["salaryScale"]:
                    enhanced_scale = {
                        "name": scale.get("name", ""),
                        "lineId": {"value": self.generate_line_id("SCALE", scale.get("name", ""))},
                        "currency": "EUR"
                    }

                    # Store reference for cross-linking
                    self.line_references[enhanced_scale["name"]] = enhanced_scale["lineId"]["value"]

                    # Transform steps
                    if "steps" in scale:
                        steps = []
                        for step in scale["steps"]:
                            enhanced_step = {
                                "name": str(step.get("zone", step.get("aanvang", ""))),
                                "value": step.get("amount", step.get("value", 0)),
                                "currency": "EUR"
                            }
                            # Add effective period if dates are available
                            if "aanvang" in step or "eind" in step:
                                enhanced_step["effectivePeriod"] = {
                                    "validFrom": str(step.get("aanvang", "")),
                                    "validTo": str(step.get("eind", ""))
                                }
                            steps.append(enhanced_step)
                        enhanced_scale["steps"] = steps

                    # Youth scales
                    if "youthScales" in scale:
                        enhanced_scale["youthScales"] = scale["youthScales"]

                    scales.append(enhanced_scale)

                enhanced_rem["salaryScale"] = scales

            # Add general increases if present
            if "generalIncrease" in rem:
                increases = []
                for increase in rem["generalIncrease"]:
                    enhanced_increase = {
                        "effectiveDate": increase.get("effectiveDate", ""),
                        "line": []
                    }

                    if "line" in increase:
                        for line in increase["line"]:
                            enhanced_line = {
                                "lineId": {"value": self.generate_line_id("INCREASE")},
                                "amount": line.get("amount", {}),
                                "interval": line.get("interval", {})
                            }
                            enhanced_increase["line"].append(enhanced_line)

                    increases.append(enhanced_increase)

                enhanced_rem["generalIncrease"] = increases

            remuneration_list.append(enhanced_rem)

        result["remuneration"] = remuneration_list

    def _transform_leave(self, data: dict[str, Any], result: dict[str, Any]):
        """Transform leave arrangements with individual leaveDayValue per type."""
        if "leave" not in data:
            return

        leave_list = []

        for leave in data["leave"]:
            enhanced_leave = {}

            # Legal leave with individual leaveDayValue
            if "legalLeave" in leave:
                legal = leave["legalLeave"].copy()
                if "entitlement" in legal:
                    # Add leaveDayValue if not present
                    if "leaveDayValue" not in legal["entitlement"]:
                        legal["entitlement"]["leaveDayValue"] = {
                            "value": 0,  # Calculate based on salary
                            "currency": "EUR",
                            "description": "Day value for legal leave"
                        }
                    # Add lineId for cross-referencing
                    legal["entitlement"]["lineId"] = {
                        "value": self.generate_line_id("LEAVE", "LEGAL")
                    }
                enhanced_leave["legalLeave"] = legal

            # Extra legal leave with individual leaveDayValue
            if "extraLegalLeave" in leave:
                extra = leave["extraLegalLeave"].copy()
                if "entitlement" in extra:
                    if "leaveDayValue" not in extra["entitlement"]:
                        extra["entitlement"]["leaveDayValue"] = {
                            "value": 0,
                            "currency": "EUR",
                            "description": "Day value for extra legal leave"
                        }
                    extra["entitlement"]["lineId"] = {
                        "value": self.generate_line_id("LEAVE", "EXTRA")
                    }
                enhanced_leave["extraLegalLeave"] = extra

            # ADV days with individual value
            if "advDays" in leave:
                adv = leave["advDays"].copy()
                if "entitlement" in adv:
                    if "leaveDayValue" not in adv["entitlement"]:
                        adv["entitlement"]["leaveDayValue"] = {
                            "value": 0,
                            "currency": "EUR",
                            "description": "Day value for ADV days"
                        }
                    adv["entitlement"]["lineId"] = {
                        "value": self.generate_line_id("LEAVE", "ADV")
                    }
                enhanced_leave["advDays"] = adv

            # Add WAZO leave support (NEW in v2.0)
            if "wazoLeave" in leave:
                wazo = leave["wazoLeave"].copy()
                if "entitlement" in wazo:
                    if "leaveDayValue" not in wazo["entitlement"]:
                        wazo["entitlement"]["leaveDayValue"] = {
                            "value": 0,
                            "currency": "EUR",
                            "description": "Day value for WAZO leave"
                        }
                    wazo["entitlement"]["lineId"] = {
                        "value": self.generate_line_id("LEAVE", "WAZO")
                    }
                enhanced_leave["wazoLeave"] = wazo

            leave_list.append(enhanced_leave)

        result["leave"] = leave_list

    def _transform_allowances(self, data: dict[str, Any], result: dict[str, Any]):
        """Transform allowances with proportional indicators and lineId."""
        if "allowance" not in data and "allowances" not in data:
            return

        allowances = data.get("allowance", data.get("allowances", []))
        enhanced_allowances = []

        for allowance in allowances:
            enhanced = allowance.copy()

            # Add lineId for cross-referencing
            enhanced["lineId"] = {
                "value": self.generate_line_id("ALLOWANCE", allowance.get("type", ""))
            }

            # Add proportional indicator for overtime and irregular hours
            allowance_type = allowance.get("type", "").lower()
            if any(x in allowance_type for x in ["overtime", "irregular", "shift"]):
                enhanced["proportional"] = True
                enhanced["proportionalDescription"] = "Pro-rata for part-time employees"

            # Ensure proper amount structure
            if "amount" in enhanced:
                if not isinstance(enhanced["amount"], dict):
                    enhanced["amount"] = {
                        "value": enhanced["amount"],
                        "currency": "EUR"
                    }

            # Add IKB reference if applicable
            if allowance.get("ikbEligible", False):
                enhanced["ikbReference"] = [{
                    "id": {"value": "IKB-001"},
                    "percentage": 100,
                    "description": "Fully eligible for IKB"
                }]

            enhanced_allowances.append(enhanced)

        result["allowance"] = enhanced_allowances

    def _transform_ikb(self, data: dict[str, Any], result: dict[str, Any]):
        """Transform IKB with enhanced references."""
        if "individualChoiceBudget" not in data:
            return

        ikb_list = []

        for ikb in data["individualChoiceBudget"]:
            enhanced_ikb = ikb.copy()

            # Add lineId
            enhanced_ikb["lineId"] = {
                "value": self.generate_line_id("IKB", ikb.get("name", ""))
            }

            # Add references to components included in IKB
            if "components" in ikb:
                references = []
                for component in ikb["components"]:
                    # Try to find matching line reference
                    if component in self.line_references:
                        references.append({
                            "id": {"value": self.line_references[component]},
                            "relationType": "INCLUDES"
                        })

                if references:
                    enhanced_ikb["reference"] = references

            ikb_list.append(enhanced_ikb)

        result["individualChoiceBudget"] = ikb_list

    def _enhance_pension(self, pension_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Enhance pension data with v2.0 features."""
        enhanced_pension = []

        for pension in pension_data:
            enhanced = pension.copy()

            # Add lineId for cross-referencing
            enhanced["lineId"] = {
                "value": self.generate_line_id("PENSION", pension.get("provider", ""))
            }

            # Store reference
            if "provider" in pension:
                self.line_references[f"PENSION_{pension['provider']}"] = enhanced["lineId"]["value"]

            enhanced_pension.append(enhanced)

        return enhanced_pension

    def _add_supplementary_arrangement(self, data: dict[str, Any], result: dict[str, Any]):
        """Add supplementaryArrangement for RVU/generation pacts if applicable."""
        supplementary = []

        # Check for RVU (early retirement) arrangements
        if any(key in data for key in ["rvuArrangement", "earlyRetirement", "generationPact"]):
            rvu = {
                "type": "RVU",
                "lineId": {"value": self.generate_line_id("SUPPLEMENTARY", "RVU")},
                "description": "Early retirement arrangement (RVU)",
                "conditions": []
            }

            if "rvuArrangement" in data:
                rvu.update(data["rvuArrangement"])

            supplementary.append(rvu)

        # Check for generation pact
        if "generationPact" in data:
            pact = {
                "type": "GenerationPact",
                "lineId": {"value": self.generate_line_id("SUPPLEMENTARY", "GENPACT")},
                "description": "Generation pact arrangement",
                "conditions": data["generationPact"].get("conditions", [])
            }
            supplementary.append(pact)

        if supplementary:
            result["supplementaryArrangement"] = supplementary


def transform_ikea_to_march2026(input_file: Path, output_file: Path) -> Path:
    """Transform IKEA JSON to March 2026 SETU v2.0 format."""

    print(f"📖 Reading IKEA JSON from {input_file}")
    with open(input_file, encoding='utf-8') as f:
        data = json.load(f)

    print("🔄 Transforming to March 2026 SETU v2.0 format...")
    transformer = SETUv2March2026Transformer()
    transformed = transformer.transform(data)

    print(f"✅ Writing transformed JSON to {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(transformed, f, indent=2, ensure_ascii=False, default=str)

    print("📊 Transformation complete:")
    print(f"   - Added {transformer.line_id_counter - 1000} lineId references")
    print(f"   - Enhanced {len(transformer.line_references)} components with cross-references")

    return output_file


if __name__ == "__main__":
    input_path = Path("data/setu/1049-ikea-cao-1-10-2023-tm-31-12-2024-v07022024.setu.json")
    output_path = Path("data/setu/1049-ikea-cao-march2026-v2.setu.json")

    transform_ikea_to_march2026(input_path, output_path)