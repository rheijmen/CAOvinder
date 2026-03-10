"""CAO → SETU v2.0 InquiryPayEquity Mapping Registry.

This module provides a comprehensive, queryable mapping system for translating
Dutch CAO (Collective Labour Agreement) concepts into SETU v2.0 InquiryPayEquity
standard fields.

Features:
- Dutch/English terminology aliases
- Decision logic for ambiguous cases
- Validation-compliant SETU structures
- Extensibility for non-CAO documents (arbeidsovereenkomst, functieomschrijving)
- Clear examples for each mapping

Based on:
- SETU v2.0 InquiryPayEquity specification (March 2026)
- Official SETU documentation from data/setu_input/
- Real-world CAO extraction cases (Metalektro, IKEA, Achmea, Rabobank)
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class ConceptMapping:
    """Represents a mapping from CAO concept to SETU field."""

    concept_id: str  # Unique identifier
    setu_field: str  # Target SETU v2.0 field path
    setu_root_property: str  # Root-level SETU property
    description: str  # What this concept represents
    aliases_nl: list[str]  # Dutch terminology variations
    aliases_en: list[str]  # English terminology variations
    decision_logic: str  # When to use this mapping
    setu_structure: dict  # Example SETU structure
    notes: str = ""  # Additional guidance


# ============================================================================
# MAPPING REGISTRY
# ============================================================================

CONCEPT_MAPPINGS: dict[str, ConceptMapping] = {
    # ------------------------------------------------------------------------
    # SALARY ADJUSTMENTS & INCREASES
    # ------------------------------------------------------------------------
    "general_salary_increase": ConceptMapping(
        concept_id="general_salary_increase",
        setu_field="remuneration[].generalSalaryIncrease[]",
        setu_root_property="remuneration",
        description="Periodic salary increases applying to all employees (e.g., CAO-mandated raises)",
        aliases_nl=[
            "algemene loonsverhoging",
            "loonsverhoging",
            "cao-verhoging",
            "salarisverhog ing",
            "loonsverhogingsafspraak",
            "periodicale verhoging",
        ],
        aliases_en=[
            "general salary increase",
            "wage increase",
            "salary raise",
            "periodic increase",
            "cao raise",
        ],
        decision_logic="""
        Use generalSalaryIncrease when:
        - Applies to ALL employees (not individual)
        - Periodic/recurring (has effective dates)
        - Part of CAO agreement
        - Usually percentage-based

        NOT for:
        - Individual performance raises (use individualSalaryIncrease)
        - One-time bonuses (use supplementaryArrangement)
        """,
        setu_structure={
            "remuneration": [
                {
                    "origin": {"type": "CollectiveLabourAgreement"},
                    "workDuration": {"amount": {"value": 38, "unitCode": "Hour"}},
                    "interval": {"value": 1, "unitCode": "Month"},
                    "salaryScale": [...],
                    "generalSalaryIncrease": [
                        {
                            "effectivePeriod": {"validFrom": "2024-06-01"},
                            "percentage": 2.75,  # 2.75%
                            "minimumAmount": {"value": 74.43, "currency": "EUR"},
                        },
                        {
                            "effectivePeriod": {"validFrom": "2025-01-01"},
                            "percentage": 3.25,
                            "minimumAmount": {"value": 90.82, "currency": "EUR"},
                        },
                    ],
                }
            ]
        },
        notes="Metalektro CAO 2024-2025 has 3 scheduled increases. Always include effectivePeriod.validFrom.",
    ),
    "individual_salary_increase": ConceptMapping(
        concept_id="individual_salary_increase",
        setu_field="remuneration[].individualSalaryIncrease[]",
        setu_root_property="remuneration",
        description="Individual salary step increases (periodieke verhogingen within salary scales)",
        aliases_nl=[
            "periodiek",
            "periodieke verhoging",
            "trede",
            "tredes",
            "salaristrede",
            "individuele verhoging",
        ],
        aliases_en=[
            "periodic increase",
            "salary step",
            "individual increase",
            "step increase",
        ],
        decision_logic="""
        Use individualSalaryIncrease when:
        - Employee moves to next step in scale
        - Based on tenure/seniority
        - Individual progression (not CAO-wide)

        NOT for:
        - CAO-wide raises (use generalSalaryIncrease)
        """,
        setu_structure={
            "remuneration": [
                {
                    "individualSalaryIncrease": [
                        {
                            "effectivePeriod": {"validFrom": "2024-01-01"},
                            "amount": {
                                "value": 1,
                                "unitCode": "Step",
                                "baseAmount": {"unitCode": "SalaryScale"},
                            },
                            "conditions": [
                                {
                                    "conditionType": "Text",
                                    "description": "After 1 year of employment",
                                }
                            ],
                        }
                    ]
                }
            ]
        },
        notes="Typically moves employee one step up in their salary scale annually.",
    ),
    # ------------------------------------------------------------------------
    # ONE-TIME PAYMENTS & BONUSES
    # ------------------------------------------------------------------------
    "supplementary_arrangement": ConceptMapping(
        concept_id="supplementary_arrangement",
        setu_field="supplementaryArrangement[]",
        setu_root_property="supplementaryArrangement",
        description="One-time or temporary payments, bonuses, special arrangements",
        aliases_nl=[
            "eenmalige uitkering",
            "bonus",
            "gratificatie",
            "afbouw eenmalige uitkering",
            "bijzondere uitkering",
            "incidentele betaling",
            "tijdelijke uitkering",
        ],
        aliases_en=[
            "one-time payment",
            "bonus",
            "special payment",
            "temporary payment",
            "phase-out payment",
        ],
        decision_logic="""
        Use supplementaryArrangement when:
        - Non-recurring payment
        - One-time bonus or compensation
        - Temporary arrangement (e.g., phase-out payments)
        - Generation pact, early retirement (RVU)

        NOT for:
        - Recurring allowances (use allowance)
        - Regular salary increases (use generalSalaryIncrease)
        """,
        setu_structure={
            "supplementaryArrangement": [
                {
                    "id": {"value": "SUPP-001", "schemeAgencyId": "Customer"},
                    "name": "Afbouw eenmalige uitkering",
                    "typeCode": "OneTimePayment",
                    "effectivePeriod": {
                        "validFrom": "2024-06-01",
                        "validTo": "2024-08-31",
                    },
                    "line": [
                        {
                            "lineId": {"value": "LINE-001"},
                            "amount": {"value": 60, "unitCode": "Euro"},
                            "interval": {"value": 1, "unitCode": "Month"},
                            "conditions": [
                                {
                                    "conditionType": "Text",
                                    "description": "June, July, August 2024",
                                }
                            ],
                        }
                    ],
                }
            ]
        },
        notes="Metalektro 2024 has phase-out payments of €60 (Jun-Aug) and €50 (Sep-Dec).",
    ),
    # ------------------------------------------------------------------------
    # ALLOWANCES & SURCHARGES
    # ------------------------------------------------------------------------
    "allowance": ConceptMapping(
        concept_id="allowance",
        setu_field="allowance[]",
        setu_root_property="allowance",
        description="Recurring allowances for specific conditions (shift work, overtime, irregular hours)",
        aliases_nl=[
            "toeslag",
            "toeslagen",
            "onregelmatigheidstoeslag",
            "ort",
            "ploegentoeslag",
            "overwerktoeslag",
            "verschuivingstoeslag",
            "feestdagentoeslag",
        ],
        aliases_en=[
            "allowance",
            "surcharge",
            "shift allowance",
            "overtime allowance",
            "irregular hours allowance",
            "holiday surcharge",
        ],
        decision_logic="""
        Use allowance when:
        - Recurring compensation for specific conditions
        - Conditional on time (shift, weekend, holidays)
        - Percentage or fixed amount on top of base salary

        Examples:
        - Shift work (ploegentoeslag)
        - Irregular hours (ORT)
        - Weekend work
        - Public holiday work
        """,
        setu_structure={
            "allowance": [
                {
                    "id": {"value": "ALL-001", "schemeAgencyId": "Customer"},
                    "name": "Onregelmatigheidstoeslag (ORT)",
                    "typeCode": "HT320",  # Irregular hours code
                    "effectivePeriod": {
                        "validFrom": "2024-01-01",
                        "validTo": "2025-12-31",
                    },
                    "period": [
                        {
                            "timePeriod": {"start": "20:00:00", "end": "06:00:00"},
                            "weekday": [
                                "Monday",
                                "Tuesday",
                                "Wednesday",
                                "Thursday",
                                "Friday",
                            ],
                        }
                    ],
                    "line": [
                        {
                            "lineId": {"value": "LINE-001"},
                            "amount": {
                                "value": 20,
                                "unitCode": "Percentage",
                                "baseAmount": {"unitCode": "HourlyRate"},
                            },
                            "interval": {"value": 1, "unitCode": "Hour"},
                        }
                    ],
                }
            ]
        },
        notes="ORT typically 15-25% surcharge for evening/night/weekend hours.",
    ),
    # ------------------------------------------------------------------------
    # HOLIDAY & LEAVE
    # ------------------------------------------------------------------------
    "holiday_allowance": ConceptMapping(
        concept_id="holiday_allowance",
        setu_field="holidayAllowance[]",
        setu_root_property="holidayAllowance",
        description="Vakantiegeld - mandatory holiday allowance (typically 8% in Netherlands)",
        aliases_nl=[
            "vakantiegeld",
            "vakantie-uitkering",
            "vakantiebijslag",
        ],
        aliases_en=[
            "holiday allowance",
            "vacation allowance",
            "holiday pay",
        ],
        decision_logic="""
        Use holidayAllowance for:
        - Annual vacation payment (vakantiegeld)
        - Usually 8% of annual salary
        - Paid once per year (typically May/June)

        NOT for:
        - Vacation days/hours (use leave)
        """,
        setu_structure={
            "holidayAllowance": [
                {
                    "id": {"value": "HOL-001", "schemeAgencyId": "Customer"},
                    "origin": {"type": "CollectiveLabourAgreement"},
                    "effectivePeriod": {
                        "validFrom": "2024-01-01",
                        "validTo": "2025-12-31",
                    },
                    "line": [
                        {
                            "lineId": {"value": "LINE-001"},
                            "amount": {
                                "value": 8,
                                "unitCode": "Percentage",
                                "baseAmount": {
                                    "unitCode": "ActualWage",
                                    "baseType": "GrossSalary",
                                },
                            },
                            "payDate": {"month": 5},  # Paid in May
                        }
                    ],
                }
            ]
        },
        notes="Statutory minimum is 8% in Netherlands. Can be higher in CAOs.",
    ),
    "individual_choice_budget": ConceptMapping(
        concept_id="individual_choice_budget",
        setu_field="individualChoiceBudget[]",
        setu_root_property="individualChoiceBudget",
        description="IKB - Individual Choice Budget for flexible benefits",
        aliases_nl=[
            "ikb",
            "individueel keuzebudget",
            "keuzebudget",
            "keuzeverlof",
        ],
        aliases_en=[
            "individual choice budget",
            "ikb",
            "flexible benefits budget",
        ],
        decision_logic="""
        Use individualChoiceBudget for:
        - Budget employees can use flexibly
        - Buy extra leave days
        - Convert to cash
        - Bicycle lease, study costs, etc.
        """,
        setu_structure={
            "individualChoiceBudget": [
                {
                    "id": {"value": "IKB-001", "schemeAgencyId": "Customer"},
                    "origin": {"type": "CollectiveLabourAgreement"},
                    "effectivePeriod": {
                        "validFrom": "2024-01-01",
                        "validTo": "2025-12-31",
                    },
                    "line": [
                        {
                            "lineId": {"value": "LINE-001"},
                            "amount": {
                                "value": 2,
                                "unitCode": "Percentage",
                                "baseAmount": {"unitCode": "ActualWage"},
                            },
                            "interval": {"value": 1, "unitCode": "Year"},
                        }
                    ],
                }
            ]
        },
        notes="Typically 1-3% of annual salary. Can be spent on various benefits.",
    ),
    # ------------------------------------------------------------------------
    # OTHER ARRANGEMENTS
    # ------------------------------------------------------------------------
    "other_arrangement": ConceptMapping(
        concept_id="other_arrangement",
        setu_field="otherArrangement[]",
        setu_root_property="otherArrangement",
        description="Other arrangements that don't fit standard categories",
        aliases_nl=[
            "overige regeling",
            "bijzondere regeling",
            "specifieke regeling",
        ],
        aliases_en=[
            "other arrangement",
            "special arrangement",
            "miscellaneous arrangement",
        ],
        decision_logic="""
        Use otherArrangement when:
        - Doesn't fit other categories
        - Company-specific arrangement
        - Temporary or unique regulation
        """,
        setu_structure={"otherArrangement": []},
        notes="Catch-all for arrangements not fitting other SETU categories.",
    ),
}


# ============================================================================
# QUERY FUNCTIONS
# ============================================================================


def find_mapping_by_dutch_term(term: str) -> list[ConceptMapping]:
    """Find SETU mappings by Dutch terminology.

    Args:
        term: Dutch term to search for (case-insensitive)

    Returns:
        List of matching ConceptMapping objects

    Example:
        >>> find_mapping_by_dutch_term("eenmalige uitkering")
        [ConceptMapping(concept_id='supplementary_arrangement', ...)]
    """
    term_lower = term.lower().strip()
    matches = []

    for mapping in CONCEPT_MAPPINGS.values():
        if any(term_lower in alias.lower() for alias in mapping.aliases_nl):
            matches.append(mapping)

    return matches


def find_mapping_by_english_term(term: str) -> list[ConceptMapping]:
    """Find SETU mappings by English terminology."""
    term_lower = term.lower().strip()
    matches = []

    for mapping in CONCEPT_MAPPINGS.values():
        if any(term_lower in alias.lower() for alias in mapping.aliases_en):
            matches.append(mapping)

    return matches


def get_mapping_by_concept_id(concept_id: str) -> ConceptMapping | None:
    """Get mapping by concept ID."""
    return CONCEPT_MAPPINGS.get(concept_id)


def get_all_setu_root_properties() -> set[str]:
    """Get all SETU root-level properties used in mappings."""
    return {mapping.setu_root_property for mapping in CONCEPT_MAPPINGS.values()}


def get_mappings_by_setu_field(setu_field: str) -> list[ConceptMapping]:
    """Get all mappings that map to a specific SETU field path."""
    return [
        mapping
        for mapping in CONCEPT_MAPPINGS.values()
        if mapping.setu_field == setu_field
    ]


# ============================================================================
# VALIDATION HELPERS
# ============================================================================


def is_valid_setu_root_property(field_name: str) -> bool:
    """Check if a field name is a valid SETU v2.0 root property.

    Based on official SETU v2.0 InquiryPayEquity specification (18 root properties).
    """
    ALLOWED_ROOT_PROPERTIES = {
        "documentId",
        "versionId",
        "effectivePeriod",
        "customer",
        "remuneration",
        "leave",
        "pension",
        "benefits",
        "workingConditions",
        "training",
        "careerDevelopment",
        "healthAndSafety",
        "disputeResolution",
        "termination",
        "dataProtection",
        "amendments",
        "signatures",
        "attachments",
        # Additional root properties from SETU docs
        "allowance",
        "holidayAllowance",
        "individualChoiceBudget",
        "supplementaryArrangement",
        "otherArrangement",
        "sickPay",
        "sustainableEmployability",
        "labourAgreements",
        "baseDefinition",
        "positionProfile",
    }

    return field_name in ALLOWED_ROOT_PROPERTIES


# ============================================================================
# SMART MAPPING DECISION LOGIC
# ============================================================================


def suggest_setu_field(
    cao_text: str,
    context: dict | None = None,
) -> list[tuple[ConceptMapping, float]]:
    """Intelligently suggest SETU field(s) for a CAO concept.

    Args:
        cao_text: Text describing the CAO concept
        context: Optional context (e.g., {is_recurring: True, is_percentage: True})

    Returns:
        List of (ConceptMapping, confidence_score) tuples, sorted by confidence

    Example:
        >>> suggest_setu_field("Algemene loonsverhoging per 1 juni 2024: 2,75%")
        [(ConceptMapping(...generalSalaryIncrease...), 0.95)]
    """
    cao_text_lower = cao_text.lower()
    context = context or {}

    matches: list[tuple[ConceptMapping, float]] = []

    # Try Dutch term matching first
    for mapping in CONCEPT_MAPPINGS.values():
        confidence = 0.0

        # Exact alias match
        for alias in mapping.aliases_nl + mapping.aliases_en:
            if alias.lower() in cao_text_lower:
                confidence = max(confidence, 0.9)

        # Context-based boosting
        if context.get("is_recurring") and "salary_increase" in mapping.concept_id:
            confidence += 0.05

        if context.get("is_one_time") and "supplementary" in mapping.concept_id:
            confidence += 0.05

        if context.get("is_conditional") and mapping.concept_id == "allowance":
            confidence += 0.05

        if confidence > 0:
            matches.append((mapping, min(confidence, 1.0)))

    # Sort by confidence (highest first)
    matches.sort(key=lambda x: x[1], reverse=True)

    return matches
