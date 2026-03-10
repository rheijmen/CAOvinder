"""
Layer 2: SETU Transformer
==========================
Transform extracted facts into SETU v2.0 structure using deterministic rules.

This is the SECOND layer in our 4-layer compliance system.
"""

from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class SETUTransformer:
    """
    Layer 2: Transform facts to SETU structure using rules.

    Goal: Map unstructured facts to SETU schema
    Output: SETU-structured JSON (may have errors)
    """

    def __init__(self):
        # Load transformation rules
        self.rules = self._build_transformation_rules()

    def _build_transformation_rules(self) -> dict:
        """
        Build the transformation rule library.

        These are DETERMINISTIC rules learned from valid examples.
        """
        return {
            "document_id": self._transform_document_id,
            "version_id": self._transform_version_id,
            "holiday_allowance": self._transform_holiday_allowance,
            "salary_scale": self._transform_salary_scale,
            "pension": self._transform_pension,
            "effective_period": self._transform_effective_period,
        }

    def transform(self, facts: dict[str, Any]) -> dict[str, Any]:
        """
        Transform facts to SETU structure.

        Apply transformation rules to map facts → SETU fields.
        """
        logger.info("Transforming facts to SETU structure", fact_count=len(facts))

        setu = {
            # Required fields with defaults
            "documentId": self._transform_document_id(facts),
            "effectivePeriod": self._transform_effective_period(facts),
            "customer": self._transform_customer(facts),
            "remuneration": self._transform_remuneration(facts)
        }

        # Optional fields
        if "document" in facts and "version" in facts["document"]:
            setu["versionId"] = self._transform_version_id(facts)

        if "holiday_allowance" in facts:
            setu["holidayAllowance"] = self._transform_holiday_allowance(facts)

        if "pension" in facts:
            setu["pension"] = self._transform_pension(facts)

        logger.info(
            "Transformation complete",
            fields_created=len(setu),
            has_remuneration=bool(setu.get("remuneration")),
            has_holiday=bool(setu.get("holidayAllowance"))
        )

        return setu

    def _transform_document_id(self, facts: dict) -> dict:
        """Transform document info to documentId."""
        if "document" in facts and "name" in facts["document"]:
            # Extract CAO name and create ID
            name = facts["document"]["name"]
            # Clean name: "CAO Achmea" → "achmea-cao"
            clean_name = name.lower().replace("cao ", "").replace(" ", "-")

            # Add dates if available
            if "valid_from" in facts["document"]:
                from_date = facts["document"]["valid_from"]
                to_date = facts["document"].get("valid_until", "")
                doc_id = f"{clean_name}-{from_date}-tm-{to_date}".replace("/", "-")
            else:
                doc_id = clean_name

            return {
                "value": doc_id,
                "schemeAgencyId": clean_name.split("-")[0]  # First part as agency
            }

        # Fallback
        return {"value": "unknown-cao", "schemeAgencyId": "unknown"}

    def _transform_version_id(self, facts: dict) -> dict:
        """Transform version info to versionId object."""
        if "document" in facts and "version" in facts["document"]:
            version = facts["document"]["version"]
            # Clean version: "27-06-2024" → "v27062024"
            if "-" in version or "/" in version:
                clean_version = "v" + version.replace("-", "").replace("/", "")
            else:
                clean_version = version

            return {"value": clean_version}

        # Fallback to current date
        return {"value": f"v{datetime.now().strftime('%Y%m%d')}"}

    def _transform_effective_period(self, facts: dict) -> dict:
        """Transform validity dates to effectivePeriod."""
        period = {}

        if "document" in facts:
            if "valid_from" in facts["document"]:
                # Convert to ISO date format
                from_date = facts["document"]["valid_from"]
                period["validFrom"] = self._normalize_date(from_date)

            if "valid_until" in facts["document"]:
                to_date = facts["document"]["valid_until"]
                period["validTo"] = self._normalize_date(to_date)

        # Fallback if no dates found
        if "validFrom" not in period:
            period["validFrom"] = "2024-01-01"

        return period

    def _transform_customer(self, facts: dict) -> dict:
        """Transform to customer info."""
        if "document" in facts and "name" in facts["document"]:
            name = facts["document"]["name"]
            # Extract organization name
            org_name = name.replace("CAO ", "").strip()
            return {
                "name": org_name,
                "legalId": [
                    {
                        "value": org_name.lower().replace(" ", "-"),
                        "schemeAgencyId": "KvK"
                    }
                ],
                "personContacts": [
                    {
                        "name": {
                            "formattedName": "CAO Administrator"
                        },
                        "roleCode": "Authorized Contact"
                    }
                ]
            }

        return {
            "name": "Unknown",
            "legalId": [{"value": "unknown", "schemeAgencyId": "KvK"}],
            "personContacts": [
                {
                    "name": {"formattedName": "Unknown"},
                    "roleCode": "Authorized Contact"
                }
            ]
        }

    def _transform_holiday_allowance(self, facts: dict) -> list[dict]:
        """
        Transform holiday allowance facts to SETU structure.

        This is THE CRITICAL transformation that was failing before.
        """
        if "holiday_allowance" not in facts:
            return []

        ha = facts["holiday_allowance"]

        # Build SETU structure
        holiday_allowance = {
            "origin": {"type": "CollectiveLabourAgreement"},
            "line": []
        }

        # Add percentage as amount
        if "percentage" in ha:
            holiday_allowance["line"].append({
                "amount": {
                    "baseAmount": {"value": float(ha["percentage"])},
                    "proportional": {"baseDefinition": "salary"}
                }
            })

        # Add payment date if available
        if "payment_month" in ha:
            month_map = {
                "January": 1, "February": 2, "March": 3, "April": 4,
                "May": 5, "June": 6, "July": 7, "August": 8,
                "September": 9, "October": 10, "November": 11, "December": 12,
                "januari": 1, "februari": 2, "maart": 3, "april": 4,
                "mei": 5, "juni": 6, "juli": 7, "augustus": 8,
                "september": 9, "oktober": 10, "november": 11, "december": 12
            }
            month = month_map.get(ha["payment_month"], 5)  # Default May
            holiday_allowance["payDate"] = {"month": month}

        return [holiday_allowance]

    def _transform_pension(self, facts: dict) -> list[dict]:
        """Transform pension facts to SETU structure."""
        if "pension" not in facts:
            return []

        p = facts["pension"]

        pension = {
            "origin": {"type": "CollectiveLabourAgreement"},
            "line": []
        }

        # Add employer contribution
        if "employer_percentage" in p:
            pension["line"].append({
                "amount": {
                    "baseAmount": {"value": float(p["employer_percentage"])},
                    "proportional": {"baseDefinition": "salary"}
                },
                "description": "Employer contribution"
            })

        # Add employee contribution
        if "employee_percentage" in p:
            pension["line"].append({
                "amount": {
                    "baseAmount": {"value": float(p["employee_percentage"])},
                    "proportional": {"baseDefinition": "salary"}
                },
                "description": "Employee contribution"
            })

        return [pension]

    def _transform_remuneration(self, facts: dict) -> list[dict]:
        """Transform salary and allowance facts to remuneration."""
        remuneration_list = []

        # Extract salary scales from multiple possible field structures
        scales = None

        # Check for direct "salary_scales" field
        if "salary_scales" in facts:
            scales = facts["salary_scales"]

        # Check for nested "salary_information" structure
        elif "salary_information" in facts:
            salary_info = facts["salary_information"]
            # Look for nested salary scales with various names
            for key in ["salary_scales_2023", "salary_scales_2024", "salary_scales", "scales"]:
                if key in salary_info:
                    scales = salary_info[key]
                    break

        # Extract work duration from salary_information
        work_hours = 40  # Default
        if "salary_information" in facts and "standard_workweek_hours" in facts["salary_information"]:
            work_hours = facts["salary_information"]["standard_workweek_hours"]

        # Transform salary scales if found
        if scales and isinstance(scales, list):
            for scale in scales:
                rem = {
                    "origin": {"type": "CollectiveLabourAgreement"},
                    "workDuration": {
                        "value": work_hours,
                        "unitCode": "HUR"
                    },
                    "interval": "Month",
                    "salaryScale": [self._transform_salary_scale(scale)]
                }
                remuneration_list.append(rem)

        # If no salary scales, create minimal remuneration
        if not remuneration_list:
            remuneration_list.append({
                "origin": {"type": "CollectiveLabourAgreement"},
                "workDuration": {
                    "value": work_hours,
                    "unitCode": "HUR"
                },
                "interval": "Month",
                "salaryScale": []
            })

        return remuneration_list

    def _transform_salary_scale(self, scale: dict) -> dict:
        """Transform a single salary scale."""
        # Get scale name - check both "group" and "scale" fields
        scale_name = scale.get('group', scale.get('scale', 'Unknown'))

        setu_scale = {
            "name": f"Group {scale_name}",
            "currency": "EUR"
        }

        # Handle min value - check both "min" and "minimum" fields
        if "min" in scale:
            setu_scale["minValue"] = float(scale["min"])
        elif "minimum" in scale:
            setu_scale["minValue"] = float(scale["minimum"])

        # Handle max value - check both "max" and "maximum" fields
        if "max" in scale:
            setu_scale["maxValue"] = float(scale["max"])
        elif "maximum" in scale:
            setu_scale["maxValue"] = float(scale["maximum"])

        # Transform steps if available
        if "steps" in scale and isinstance(scale["steps"], list):
            setu_scale["salaryStep"] = [
                {"value": float(step)} for step in scale["steps"]
            ]

        return setu_scale

    def _normalize_date(self, date_str: str) -> str:
        """Normalize date to ISO format YYYY-MM-DD."""
        # Try common formats
        date_str = date_str.replace("/", "-")
        parts = date_str.split("-")

        if len(parts) == 3:
            # Assume DD-MM-YYYY or YYYY-MM-DD
            if len(parts[0]) == 4:
                # Already YYYY-MM-DD
                return date_str
            else:
                # Convert DD-MM-YYYY to YYYY-MM-DD
                return f"{parts[2]}-{parts[1]:0>2}-{parts[0]:0>2}"

        # Fallback
        return date_str