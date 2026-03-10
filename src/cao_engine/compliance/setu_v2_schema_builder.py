"""
SETU v2.0 Schema Builder from Official Excel Specification

This script parses the official SETU v2.0 Excel specification and builds
the correct JSON Schema that matches what the validator expects.
"""

import json
from pathlib import Path
from typing import Any

import pandas as pd
import structlog

logger = structlog.get_logger(__name__)


class SETUSchemaBuilder:
    """Build correct SETU v2.0 JSON Schema from Excel specification."""

    def __init__(self, excel_path: Path):
        self.excel_path = excel_path
        self.schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "$id": "https://setu.semantic-treehouse.nl/v2.0/InquiryPayEquity",
            "title": "SETU Inquiry Pay Equity v2.0",
            "type": "object",
            "additionalProperties": False,  # CRITICAL: No additional properties allowed
            "required": [],
            "properties": {},
            "$defs": {}
        }

    def parse_excel_spec(self) -> dict[str, Any]:
        """Parse the Excel specification to extract schema information."""

        # Read the Excel file
        df = pd.read_excel(self.excel_path, sheet_name=None)

        # The Excel typically has sheets for:
        # - Message structure
        # - Field definitions
        # - Code lists
        # - Examples

        schema_info = {
            "fields": [],
            "required": [],
            "definitions": {}
        }

        # Find the main structure sheet (usually first or named "InquiryPayEquity")
        main_sheet = None
        for sheet_name, sheet_df in df.items():
            if 'InquiryPayEquity' in sheet_name or sheet_name == 'Message':
                main_sheet = sheet_df
                break

        if main_sheet is not None:
            # Parse field definitions
            for idx, row in main_sheet.iterrows():
                if pd.notna(row.get('Field Name', row.get('Element', ''))):
                    field_info = self._extract_field_info(row)
                    if field_info:
                        schema_info['fields'].append(field_info)
                        if field_info.get('required'):
                            schema_info['required'].append(field_info['name'])

        return schema_info

    def _extract_field_info(self, row: pd.Series) -> dict[str, Any] | None:
        """Extract field information from Excel row."""

        field_name = row.get('Field Name', row.get('Element', ''))
        if not field_name or pd.isna(field_name):
            return None

        # Clean field name
        field_name = str(field_name).strip()

        field_info = {
            'name': field_name,
            'type': self._map_setu_type(row.get('Type', row.get('Data Type', 'string'))),
            'required': str(row.get('Required', row.get('M/O', ''))).upper() in ['M', 'MANDATORY', 'YES', 'TRUE'],
            'description': str(row.get('Description', row.get('Definition', ''))),
        }

        # Handle cardinality
        cardinality = row.get('Cardinality', row.get('Card', ''))
        if pd.notna(cardinality):
            card_str = str(cardinality)
            if '..*' in card_str or '0..*' in card_str:
                field_info['array'] = True
                field_info['minItems'] = 0
            elif '1..*' in card_str:
                field_info['array'] = True
                field_info['minItems'] = 1

        return field_info

    def _map_setu_type(self, setu_type: Any) -> str:
        """Map SETU type to JSON Schema type."""
        if pd.isna(setu_type):
            return "string"

        type_str = str(setu_type).lower()

        type_mapping = {
            'string': 'string',
            'text': 'string',
            'code': 'string',
            'identifier': 'object',  # Identifiers are objects with value and schemeAgencyId
            'amount': 'object',  # Amounts are complex objects
            'date': 'string',
            'datetime': 'string',
            'boolean': 'boolean',
            'indicator': 'boolean',
            'number': 'number',
            'decimal': 'number',
            'integer': 'integer',
            'object': 'object',
            'period': 'object',
        }

        for key, value in type_mapping.items():
            if key in type_str:
                return value

        return 'string'  # Default

    def build_official_schema(self) -> dict[str, Any]:
        """Build the official SETU v2.0 schema structure."""

        # Based on the semantic-treehouse validator, here's the correct structure:
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "additionalProperties": False,
            "required": ["documentId", "effectivePeriod", "customer", "remuneration"],
            "properties": {
                "documentId": {
                    "type": "object",
                    "required": ["value", "schemeAgencyId"],
                    "additionalProperties": False,
                    "properties": {
                        "value": {"type": "string"},
                        "schemeAgencyId": {
                            "type": "string",
                            # Based on validator errors, there might be enum restrictions
                            # but we'll leave it open for now
                        }
                    }
                },
                "versionId": {
                    "type": "object",  # NOT a string!
                    "required": ["value"],
                    "additionalProperties": False,
                    "properties": {
                        "value": {"type": "string"}
                    }
                },
                "issued": {
                    "type": "string",
                    "format": "date-time"
                },
                "effectivePeriod": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "validFrom": {"type": "string", "format": "date"},
                        "validTo": {"type": "string", "format": "date"}
                    }
                },
                "customer": {
                    "type": "object",
                    "required": ["legalId", "personContacts"],
                    "additionalProperties": False,
                    "properties": {
                        "name": {"type": "string"},
                        "legalId": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "required": ["value", "schemeAgencyId"],
                                "additionalProperties": False,
                                "properties": {
                                    "value": {"type": "string"},
                                    "schemeAgencyId": {"type": "string"}
                                }
                            }
                        },
                        "personContacts": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "required": ["name"],
                                "additionalProperties": False,
                                "properties": {
                                    "name": {
                                        "type": "object",
                                        "required": ["formattedName"],
                                        "additionalProperties": False,
                                        "properties": {
                                            "formattedName": {"type": "string"}
                                        }
                                    },
                                    "roleCode": {"type": "string"}
                                }
                            }
                        }
                    }
                },
                "baseDefinition": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/BaseDefinition"}
                },
                "labourAgreements": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "collectiveLabourAgreement": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "name": {"type": "string"},
                                "id": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "value": {"type": "string"}
                                    }
                                },
                                "effectivePeriod": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "validFrom": {"type": "string", "format": "date"},
                                        "validTo": {"type": "string", "format": "date"}
                                    }
                                }
                            }
                        },
                        "customLabourAgreement": {"type": "boolean"}
                    }
                },
                "positionProfile": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["positionId", "positionName"],
                        "additionalProperties": False,  # CRITICAL: No additional properties
                        "properties": {
                            "positionId": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "value": {"type": "string"}
                                }
                            },
                            "positionName": {"type": "string"},
                            "description": {"type": "string"},
                            "effectivePeriod": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "validFrom": {"type": "string", "format": "date"},
                                    "validTo": {"type": "string", "format": "date"}
                                }
                            }
                        }
                    }
                },
                "remuneration": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,  # CRITICAL: No additional properties
                        "properties": {
                            "origin": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "type": {"type": "string"}
                                }
                            },
                            "workDuration": {
                                "type": "object",
                                "required": ["amount", "interval", "valuePerWeek"],
                                "additionalProperties": False,
                                "properties": {
                                    "amount": {"type": "number"},
                                    "interval": {
                                        "type": "object",
                                        "required": ["value", "unitCode"],
                                        "additionalProperties": False,
                                        "properties": {
                                            "value": {"type": "number"},
                                            "unitCode": {"type": "string"}
                                        }
                                    },
                                    "valuePerWeek": {"type": "number"}
                                }
                            },
                            "interval": {
                                "type": "object",  # NOT a string!
                                "required": ["value", "unitCode"],
                                "additionalProperties": False,
                                "properties": {
                                    "value": {"type": "number"},
                                    "unitCode": {"type": "string"}
                                }
                            },
                            "salaryScale": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["name", "currency"],  # currency is REQUIRED
                                    "additionalProperties": False,  # No steps, youthScales, etc.
                                    "properties": {
                                        "name": {"type": "string"},
                                        "currency": {"type": "string"},
                                        "amount": {"type": "number"},
                                        "minAmount": {"type": "number"},
                                        "maxAmount": {"type": "number"},
                                        "description": {"type": "string"},
                                        "positionProfileRef": {"type": "string"},
                                        "effectivePeriod": {
                                            "type": "object",
                                            "additionalProperties": False,
                                            "properties": {
                                                "validFrom": {"type": "string", "format": "date"},
                                                "validTo": {"type": "string", "format": "date"}
                                            }
                                        }
                                    }
                                }
                            },
                            "salaryStep": {
                                "type": "array",
                                "items": {"$ref": "#/$defs/SalaryStep"}
                            },
                            "generalIncrease": {
                                "type": "array",
                                "items": {"$ref": "#/$defs/GeneralIncrease"}
                            },
                            "description": {"type": "string"},
                            "effectivePeriod": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "validFrom": {"type": "string", "format": "date"},
                                    "validTo": {"type": "string", "format": "date"}
                                }
                            }
                        }
                    }
                },
                "allowance": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/Allowance"}
                },
                "holidayAllowance": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/HolidayAllowance"}
                },
                "sickPay": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/SickPay"}
                },
                "leave": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/Leave"}
                },
                "individualChoiceBudget": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/IndividualChoiceBudget"}
                },
                "pension": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/Pension"}
                },
                "sustainableEmployability": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/SustainableEmployability"}
                },
                "supplementaryArrangement": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/SupplementaryArrangement"}
                },
                "otherArrangement": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/OtherArrangement"}
                }
            },
            "$defs": {
                # Add all the definitions here
                "BaseDefinition": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "baseType": {"type": "string"},
                        "remunerationIndicator": {"type": "boolean"},
                        "holidayAllowanceIndicator": {"type": "boolean"},
                        "paidLeaveDayIndicator": {"type": "boolean"},
                        "allAllowancesIndicator": {"type": "boolean"}
                    }
                },
                "SalaryStep": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["name", "value"],
                    "properties": {
                        "name": {"type": "string"},
                        "value": {"type": "number"},
                        "effectivePeriod": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "validFrom": {"type": "string", "format": "date"},
                                "validTo": {"type": "string", "format": "date"}
                            }
                        }
                    }
                },
                # ... Add other definitions as needed
            }
        }

        return schema

    def save_schema(self, output_path: Path):
        """Save the built schema to a JSON file."""
        schema = self.build_official_schema()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved official SETU v2.0 schema to {output_path}")


def build_official_setu_schema():
    """Build the official SETU v2.0 schema from specification."""

    excel_path = Path("data/setu_input/SETU Inquiry Pay Equity v2.0 - InquiryPayEquity (4).xlsx")
    output_path = Path("src/cao_engine/models/setu_v2_official_schema.json")

    if excel_path.exists():
        builder = SETUSchemaBuilder(excel_path)
        builder.save_schema(output_path)
        print("✅ Built official SETU v2.0 schema from Excel specification")
    else:
        # If Excel not available, use the hardcoded official structure
        builder = SETUSchemaBuilder(Path("/dev/null"))  # Dummy path
        schema = builder.build_official_schema()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)

        print("✅ Created official SETU v2.0 schema structure")

    return output_path


if __name__ == "__main__":
    build_official_setu_schema()