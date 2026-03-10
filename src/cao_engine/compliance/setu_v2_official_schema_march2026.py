"""
SETU v2.0 Official Schema - March 11, 2026 Update

This module defines the official SETU v2.0 Inquiry Pay Equity schema
based on the March 11, 2026 publication.

Key changes from v1.0 to v2.0:
1. New baseDefinition block for explicit base salary calculations
2. supplementaryArrangement for RVU and generation pacts
3. lineId for cross-referencing between components
4. proportional indicators for pro-rata calculations
5. Expanded workDuration with interval specification
6. WAZO leave support
7. Individual leaveDayValue per leave type
"""

import json
from pathlib import Path
from typing import Any


def build_setu_v2_march2026_schema() -> dict[str, Any]:
    """
    Build the official SETU v2.0 schema as published March 11, 2026.

    This schema represents the complete Inquiry Pay Equity v2.0 standard.
    """

    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://setu.semantic-treehouse.nl/v2.0/InquiryPayEquity",
        "title": "SETU Inquiry Pay Equity v2.0 (March 2026)",
        "description": "Version 2.0 of the Inquiry Pay Equity standard published March 11, 2026",
        "type": "object",
        "additionalProperties": False,
        "required": ["documentId", "effectivePeriod", "customer", "remuneration"],
        "properties": {
            # Document metadata
            "documentId": {
                "type": "object",
                "required": ["value", "schemeAgencyId"],
                "additionalProperties": False,
                "properties": {
                    "value": {
                        "type": "string",
                        "description": "Unique identifier for this document"
                    },
                    "schemeAgencyId": {
                        "type": "string",
                        "description": "Organization that issues the identifier"
                    }
                }
            },
            "versionId": {
                "type": "object",
                "required": ["value"],
                "additionalProperties": False,
                "properties": {
                    "value": {
                        "type": "string",
                        "description": "Version identifier"
                    }
                }
            },
            "issued": {
                "type": "string",
                "format": "date-time",
                "description": "Date/time when document was issued"
            },
            "effectivePeriod": {
                "$ref": "#/$defs/Period"
            },

            # Customer information
            "customer": {
                "type": "object",
                "required": ["legalId", "personContacts"],
                "additionalProperties": False,
                "properties": {
                    "id": {
                        "type": "array",
                        "maxItems": 2,
                        "items": {"$ref": "#/$defs/Identifier"}
                    },
                    "name": {"type": "string"},
                    "legalId": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"$ref": "#/$defs/Identifier"}
                    },
                    "personContacts": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"$ref": "#/$defs/PersonContact"}
                    }
                }
            },

            # NEW in v2.0: Base Definitions
            "baseDefinition": {
                "type": "array",
                "description": "Defines what components are included in base salary calculations",
                "items": {
                    "type": "object",
                    "required": ["baseType", "remunerationIndicator", "holidayAllowanceIndicator",
                                "paidLeaveDayIndicator", "allAllowancesIndicator"],
                    "additionalProperties": False,
                    "properties": {
                        "baseType": {
                            "type": "string",
                            "description": "Type of base (e.g., actualWage, BaseWage)"
                        },
                        "remunerationIndicator": {
                            "type": "boolean",
                            "description": "Whether remuneration is included in this base"
                        },
                        "holidayAllowanceIndicator": {
                            "type": "boolean",
                            "description": "Whether holiday allowance is included"
                        },
                        "paidLeaveDayIndicator": {
                            "type": "boolean",
                            "description": "Whether paid leave days are included"
                        },
                        "allAllowancesIndicator": {
                            "type": "boolean",
                            "description": "If true, all allowances included; if false, only those listed"
                        },
                        "allowances": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "typeCode": {"type": "string"}
                                }
                            }
                        },
                        "referenceDate": {
                            "$ref": "#/$defs/OccurrenceType",
                            "description": "Reference date (peildatum) for calculations"
                        }
                    }
                }
            },

            # Labour agreements
            "labourAgreements": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "industryIdentifier": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/ValueObject"}
                    },
                    "collectiveLabourAgreement": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "name": {"type": "string"},
                            "id": {"$ref": "#/$defs/ValueObject"},
                            "effectivePeriod": {"$ref": "#/$defs/Period"},
                            "basedOn": {"type": "string"}
                        }
                    },
                    "customLabourAgreement": {"type": "boolean"}
                }
            },

            # Position profiles
            "positionProfile": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["positionId", "positionName"],
                    "additionalProperties": False,
                    "properties": {
                        "positionId": {"$ref": "#/$defs/ValueObject"},
                        "positionName": {"type": "string"},
                        "origin": {"$ref": "#/$defs/Origin"},
                        "description": {"type": "string"},
                        "workDescription": {"type": "string"},
                        "effectivePeriod": {"$ref": "#/$defs/Period"}
                    }
                }
            },

            # Remuneration (significantly updated in v2.0)
            "remuneration": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "origin": {"$ref": "#/$defs/Origin"},
                        "workDuration": {
                            "type": "object",
                            "description": "Expanded in v2.0 with interval specification",
                            "additionalProperties": False,
                            "properties": {
                                "amount": {
                                    "type": "object",
                                    "properties": {
                                        "value": {"type": "number"},
                                        "unitCode": {"type": "string"}
                                    }
                                },
                                "interval": {
                                    "$ref": "#/$defs/Interval",
                                    "description": "NEW in v2.0: Interval specification"
                                },
                                "valuePerWeek": {
                                    "type": "number",
                                    "description": "Hours per week"
                                }
                            }
                        },
                        "interval": {"$ref": "#/$defs/Interval"},
                        "salaryScale": {
                            "type": "array",
                            "description": "Moved to remuneration in v2.0",
                            "items": {
                                "type": "object",
                                "required": ["name"],
                                "additionalProperties": False,
                                "properties": {
                                    "name": {"type": "string"},
                                    "currency": {
                                        "type": "string",
                                        "description": "NEW in v2.0: Currency field"
                                    },
                                    "amount": {"type": "number"},
                                    "minAmount": {"type": "number"},
                                    "maxAmount": {"type": "number"},
                                    "description": {"type": "string"},
                                    "positionProfileReference": {
                                        "type": "object",
                                        "description": "NEW in v2.0: Link to position profiles",
                                        "properties": {
                                            "positionProfileId": {"$ref": "#/$defs/ValueObject"},
                                            "startSalaryStep": {"type": "string"}
                                        }
                                    },
                                    "effectivePeriod": {"$ref": "#/$defs/Period"}
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
                        "individualSalaryIncrease": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "effectiveDate": {
                                        "$ref": "#/$defs/OccurrenceType",
                                        "description": "NEW in v2.0: Effective date"
                                    },
                                    "line": {"$ref": "#/$defs/Line"}
                                }
                            }
                        },
                        "description": {"type": "string"},
                        "effectivePeriod": {"$ref": "#/$defs/Period"}
                    }
                }
            },

            # Allowances (updated structure in v2.0)
            "allowance": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"$ref": "#/$defs/ValueObject"},
                        "origin": {"$ref": "#/$defs/Origin"},
                        "name": {"type": "string"},
                        "typeCode": {"type": "string"},
                        "description": {"type": "string"},
                        "effectivePeriod": {"$ref": "#/$defs/Period"},
                        "period": {
                            "type": "object",
                            "properties": {
                                "datePeriod": {"$ref": "#/$defs/Period"},
                                "timePeriod": {
                                    "type": "object",
                                    "properties": {
                                        "startTime": {"type": "string", "format": "time"},
                                        "endTime": {"type": "string", "format": "time"}
                                    }
                                },
                                "weekday": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                        "enum": ["Monday", "Tuesday", "Wednesday", "Thursday",
                                                "Friday", "Saturday", "Sunday", "Holidays"]
                                    }
                                }
                            }
                        },
                        "line": {
                            "type": "array",
                            "items": {"$ref": "#/$defs/LineWithId"}
                        }
                    }
                }
            },

            # Holiday allowance
            "holidayAllowance": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "origin": {"$ref": "#/$defs/Origin"},
                        "payDate": {"$ref": "#/$defs/OccurrenceType"},
                        "description": {
                            "type": "string",
                            "description": "NEW in v2.0: Description field"
                        },
                        "effectivePeriod": {"$ref": "#/$defs/Period"},
                        "line": {
                            "type": "array",
                            "items": {"$ref": "#/$defs/LineWithId"}
                        }
                    }
                }
            },

            # Sick pay (updated in v2.0)
            "sickPay": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "origin": {"$ref": "#/$defs/Origin"},
                        "waitingDays": {
                            "type": "number",
                            "description": "Moved to main level in v2.0"
                        },
                        "description": {
                            "type": "string",
                            "description": "NEW in v2.0: Description field"
                        },
                        "effectivePeriod": {"$ref": "#/$defs/Period"},
                        "line": {
                            "type": "array",
                            "items": {"$ref": "#/$defs/LineWithId"}
                        }
                    }
                }
            },

            # Leave (significantly restructured in v2.0)
            "leave": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "origin": {"$ref": "#/$defs/Origin"},
                        "description": {
                            "type": "string",
                            "description": "NEW in v2.0: Description field"
                        },
                        "effectivePeriod": {"$ref": "#/$defs/Period"},
                        "workingHoursReduction": {
                            "type": "array",
                            "description": "ADV/ATV days",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "amount": {"$ref": "#/$defs/Amount"},
                                    "leaveDayValue": {
                                        "$ref": "#/$defs/Amount",
                                        "description": "NEW in v2.0: Individual leaveDayValue"
                                    },
                                    "line": {"type": "array", "items": {"$ref": "#/$defs/LineWithId"}}
                                }
                            }
                        },
                        "paidLeave": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "amount": {"$ref": "#/$defs/Amount"},
                                    "leaveDayValue": {
                                        "$ref": "#/$defs/Amount",
                                        "description": "NEW in v2.0: Individual leaveDayValue"
                                    },
                                    "line": {"type": "array", "items": {"$ref": "#/$defs/LineWithId"}}
                                }
                            }
                        },
                        "specialLeave": {
                            "type": "array",
                            "description": "Restructured as array in v2.0",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "amount": {"$ref": "#/$defs/Amount"},
                                    "interval": {"$ref": "#/$defs/Interval"},
                                    "leaveDayValue": {"$ref": "#/$defs/Amount"},
                                    "conditions": {
                                        "type": "array",
                                        "items": {"$ref": "#/$defs/Condition"}
                                    }
                                }
                            }
                        },
                        "holidays": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "amount": {"$ref": "#/$defs/Amount"},
                                    "leaveDayValue": {"$ref": "#/$defs/Amount"}
                                }
                            }
                        },
                        "additionalParentalLeave": {
                            "type": "array",
                            "description": "NEW in v2.0: WAZO leave support",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "amount": {"$ref": "#/$defs/Amount"},
                                    "conditions": {
                                        "type": "array",
                                        "items": {"$ref": "#/$defs/Condition"}
                                    }
                                }
                            }
                        }
                    }
                }
            },

            # Individual Choice Budget
            "individualChoiceBudget": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"$ref": "#/$defs/ValueObject"},
                        "origin": {"$ref": "#/$defs/Origin"},
                        "name": {"type": "string"},
                        "description": {
                            "type": "string",
                            "description": "NEW in v2.0: Description field"
                        },
                        "effectivePeriod": {"$ref": "#/$defs/Period"},
                        "line": {
                            "type": "array",
                            "items": {"$ref": "#/$defs/LineWithId"}
                        }
                    }
                }
            },

            # Pension
            "pension": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "origin": {"$ref": "#/$defs/Origin"},
                        "name": {"type": "string"},
                        "provider": {"type": "string"},
                        "description": {
                            "type": "string",
                            "description": "NEW in v2.0: Description field"
                        },
                        "effectivePeriod": {"$ref": "#/$defs/Period"},
                        "line": {
                            "type": "array",
                            "items": {"$ref": "#/$defs/LineWithId"}
                        }
                    }
                }
            },

            # Sustainable Employability
            "sustainableEmployability": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "origin": {"$ref": "#/$defs/Origin"},
                        "name": {"type": "string"},
                        "typeCode": {"type": "string"},
                        "description": {
                            "type": "string",
                            "description": "NEW in v2.0: Description field"
                        },
                        "effectivePeriod": {"$ref": "#/$defs/Period"},
                        "line": {
                            "type": "array",
                            "items": {"$ref": "#/$defs/LineWithId"}
                        }
                    }
                }
            },

            # NEW in v2.0: Supplementary Arrangement
            "supplementaryArrangement": {
                "type": "array",
                "description": "NEW in v2.0: For RVU, generation pact, etc.",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "origin": {"$ref": "#/$defs/Origin"},
                        "name": {"type": "string"},
                        "typeCode": {
                            "type": "string",
                            "enum": ["GenerationPact", "RVU", "Other"]
                        },
                        "description": {"type": "string"},
                        "effectivePeriod": {"$ref": "#/$defs/Period"},
                        "line": {
                            "type": "array",
                            "items": {"$ref": "#/$defs/LineWithId"}
                        }
                    }
                }
            },

            # Other arrangements
            "otherArrangement": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "origin": {"$ref": "#/$defs/Origin"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "effectivePeriod": {"$ref": "#/$defs/Period"},
                        "line": {
                            "type": "array",
                            "items": {"$ref": "#/$defs/LineWithId"}
                        }
                    }
                }
            }
        },

        # Definitions
        "$defs": {
            "ValueObject": {
                "type": "object",
                "required": ["value"],
                "additionalProperties": False,
                "properties": {
                    "value": {"type": "string"}
                }
            },

            "Identifier": {
                "type": "object",
                "required": ["value", "schemeAgencyId"],
                "additionalProperties": False,
                "properties": {
                    "value": {"type": "string"},
                    "schemeAgencyId": {"type": "string"}
                }
            },

            "Period": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "validFrom": {"type": "string", "format": "date"},
                    "validTo": {"type": "string", "format": "date"}
                }
            },

            "Origin": {
                "type": "object",
                "required": ["type"],
                "additionalProperties": False,
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["CollectiveLabourAgreement", "CustomLabourAgreement"]
                    }
                }
            },

            "OccurrenceType": {
                "type": "object",
                "required": ["occurrenceType"],
                "additionalProperties": False,
                "properties": {
                    "occurrenceType": {
                        "type": "string",
                        "enum": ["Single", "Relative", "Recurring"]
                    },
                    "date": {"type": "string"},
                    "recurringInterval": {"type": "string"},
                    "event": {"type": "string"},
                    "offset": {"type": "string"}
                }
            },

            "Interval": {
                "type": "object",
                "required": ["value", "unitCode"],
                "additionalProperties": False,
                "properties": {
                    "value": {"type": "number"},
                    "unitCode": {
                        "type": "string",
                        "enum": ["Hour", "Day", "Week", "fourWeeks", "Month", "Quarter",
                                "Year", "Shift", "Kilometer", "Occurrence", "Item"]
                    }
                }
            },

            "Amount": {
                "type": "object",
                "required": ["value", "unitCode"],
                "additionalProperties": False,
                "properties": {
                    "value": {"type": "number"},
                    "minValue": {"type": "number"},
                    "maxValue": {"type": "number"},
                    "unitCode": {
                        "type": "string",
                        "enum": ["Percentage", "Euro", "Hour", "Day", "Week",
                                "Month", "Year", "Kilometer", "SalaryStep"]
                    },
                    "baseAmount": {
                        "type": "object",
                        "properties": {
                            "unitCode": {"type": "string"},
                            "baseType": {"type": "string"},
                            "value": {"type": "number"},
                            "minValue": {"type": "number"},
                            "maxValue": {"type": "number"}
                        }
                    },
                    "proportional": {
                        "type": "object",
                        "description": "NEW in v2.0: Proportional indicators",
                        "required": ["partTimePercentage", "employmentDuration"],
                        "properties": {
                            "partTimePercentage": {"type": "boolean"},
                            "employmentDuration": {"type": "boolean"},
                            "description": {"type": "string"}
                        }
                    }
                }
            },

            "PersonContact": {
                "type": "object",
                "required": ["name"],
                "additionalProperties": False,
                "properties": {
                    "name": {
                        "type": "object",
                        "required": ["formattedName"],
                        "properties": {
                            "formattedName": {"type": "string"}
                        }
                    },
                    "roleCode": {"type": "string"},
                    "positionTitle": {"type": "string"},
                    "communication": {
                        "type": "object",
                        "properties": {
                            "phone": {
                                "type": "object",
                                "properties": {
                                    "formattedNumber": {"type": "string"}
                                }
                            },
                            "email": {
                                "type": "object",
                                "properties": {
                                    "address": {"type": "string", "format": "email"}
                                }
                            }
                        }
                    }
                }
            },

            "Condition": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "conditionType": {
                        "type": "string",
                        "enum": ["Age", "Occurrence", "Text", "Function", "Seniority",
                                "ContractType", "EmploymentDuration", "Other"]
                    },
                    "description": {"type": "string"},
                    "occurrence": {"$ref": "#/$defs/OccurrenceType"},
                    "age": {
                        "type": "object",
                        "properties": {
                            "minAge": {"type": "number"},
                            "maxAge": {"type": "number"}
                        }
                    },
                    "function": {
                        "type": "object",
                        "properties": {
                            "positionProfileId": {"$ref": "#/$defs/ValueObject"}
                        }
                    },
                    "seniority": {
                        "type": "object",
                        "properties": {
                            "minYears": {"type": "number"},
                            "maxYears": {"type": "number"}
                        }
                    }
                }
            },

            "IkbReference": {
                "type": "object",
                "description": "NEW in v2.0: IKB cross-references",
                "required": ["relationType", "id"],
                "additionalProperties": False,
                "properties": {
                    "relationType": {"type": "string"},
                    "id": {"$ref": "#/$defs/ValueObject"},
                    "description": {"type": "string"}
                }
            },

            "Line": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "amount": {"$ref": "#/$defs/Amount"},
                    "interval": {"$ref": "#/$defs/Interval"},
                    "conditions": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/Condition"}
                    }
                }
            },

            "LineWithId": {
                "type": "object",
                "description": "NEW in v2.0: Lines with identifiers for cross-referencing",
                "additionalProperties": False,
                "properties": {
                    "lineId": {
                        "$ref": "#/$defs/ValueObject",
                        "description": "NEW in v2.0: Line identifier"
                    },
                    "amount": {"$ref": "#/$defs/Amount"},
                    "interval": {"$ref": "#/$defs/Interval"},
                    "conditions": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/Condition"}
                    },
                    "ikbReference": {
                        "type": "array",
                        "description": "NEW in v2.0: IKB references",
                        "items": {"$ref": "#/$defs/IkbReference"}
                    },
                    "reference": {
                        "type": "array",
                        "description": "References to other lines",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"$ref": "#/$defs/ValueObject"},
                                "relationType": {"type": "string"}
                            }
                        }
                    }
                }
            },

            "SalaryStep": {
                "type": "object",
                "required": ["name", "value"],
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "value": {"type": "number"},
                    "effectivePeriod": {"$ref": "#/$defs/Period"}
                }
            },

            "GeneralIncrease": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "effectiveDate": {"$ref": "#/$defs/OccurrenceType"},
                    "line": {"type": "array", "items": {"$ref": "#/$defs/LineWithId"}}
                }
            }
        }
    }

    return schema


def save_march2026_schema():
    """Save the March 2026 SETU v2.0 schema to file."""
    schema = build_setu_v2_march2026_schema()

    output_path = Path("src/cao_engine/models/setu_v2_march2026_schema.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved SETU v2.0 March 2026 schema to {output_path}")
    return output_path


if __name__ == "__main__":
    save_march2026_schema()