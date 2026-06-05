# SETU v2.0.0-rc.1 Pension Extraction Guide

**Version**: 1.0
**Date**: 2026-03-11
**Status**: Production-ready
**Schema**: SETU v2.0.0-rc.1 (Release Candidate 1)

## Purpose

This guide ensures all pension extractions comply with the official SETU v2.0.0-rc.1 `PensionArrangement` schema. It prevents the common mistake of creating invalid custom fields that fail schema validation.

## Critical Schema Requirements

### Required Fields (MUST be present)

1. **`name`** (string): Name or description of the pension fund or arrangement
   - Example: `"Pensioenfonds Zorg en Welzijn (PfZW)"`
   - Example: `"Rabobank Pensioenfonds - Collectieve pensioenregeling"`

2. **`origin`** (LabourAgreementReference): Type of agreement
   - ALWAYS use: `{"type": "CollectiveLabourAgreement"}`
   - Valid values: `"CollectiveLabourAgreement"`, `"CollectiveLabourAgreementExtended"`, `"CustomLabourAgreement"`, `"Unknown"`

### Optional But Recommended Fields

3. **`line[]`** (array): Contribution details
   - Each line item has: `lineId`, `amount`, `interval`, `conditions`
   - Use for employer/employee contributions, partner pension, disability coverage

4. **`franchise`** (object): Franchise amount or description
   - Use `description` field for text explanations
   - Example: `{"description": "Franchise € 17.545 (2024), jaarlijks aangepast"}`

5. **`effectivePeriod`** (object): When pension applies
   - Contains: `validFrom`, `validTo`

6. **`description`** (string): Additional details about pension scheme

## Invalid Fields (DO NOT USE)

These fields are **NOT** in the SETU v2.0 schema and will cause validation errors:

❌ `pensionFundName` → Use `name` instead
❌ `employerContribution` → Use `line[]` instead
❌ `employeeContribution` → Use `line[]` instead
❌ `pensionScheme` → Use `description` instead
❌ `pensionAge` → Not part of PensionArrangement
❌ `pensionSchemeType` → Not part of PensionArrangement
❌ `pensionableSalary` → Can be in `line[].conditions` if needed

## Valid Examples

### Example 1: Simple Pension (Sanquin CAO)

**Dutch CAO Text**:
> "De werkgever en werknemer dragen bij aan het Pensioenfonds Zorg en Welzijn (PfZW). De premieverdeling is 60% werkgever en 40% werknemer."

**Correct SETU v2.0 Structure**:
```json
{
  "pension": [{
    "name": "Pensioenfonds Zorg en Welzijn (PfZW)",
    "origin": {"type": "CollectiveLabourAgreement"},
    "effectivePeriod": {
      "validFrom": "2023-01-01",
      "validTo": "2023-12-31"
    },
    "line": [
      {
        "lineId": {"value": "EMPLOYER_CONTRIBUTION"},
        "amount": {"value": 60, "unitCode": "Percentage"},
        "interval": {"value": 1, "unitCode": "Month"},
        "conditions": [{
          "conditionType": "Text",
          "description": "Werkgeversbijdrage 60% van pensioenpremie"
        }]
      },
      {
        "lineId": {"value": "EMPLOYEE_CONTRIBUTION"},
        "amount": {"value": 40, "unitCode": "Percentage"},
        "interval": {"value": 1, "unitCode": "Month"},
        "conditions": [{
          "conditionType": "Text",
          "description": "Werknemersbijdrage 40% van pensioenpremie"
        }]
      }
    ],
    "description": "Premieverdeling 60/40 werkgever/werknemer"
  }]
}
```

### Example 2: Complex Pension (Rabobank CAO)

**Dutch CAO Text**:
> "De pensioenregeling wordt uitgevoerd door het Rabobank Pensioenfonds. Beschikbare spaarpremie 27% (werkgever 21,5%, werknemer 5,5%). Partnerpensioen op risicobasis 1,313%. Wezenpensioen 0,263%. Franchise € 17.545 (2024)."

**Correct SETU v2.0 Structure**:
```json
{
  "pension": [{
    "name": "Rabobank Pensioenfonds - Collectieve pensioenregeling",
    "origin": {"type": "CollectiveLabourAgreement"},
    "effectivePeriod": {
      "validFrom": "2024-07-01",
      "validTo": "2025-06-30"
    },
    "line": [
      {
        "lineId": {"value": "PENSION_PREMIE"},
        "amount": {"value": 27, "unitCode": "Percentage"},
        "interval": {"value": 1, "unitCode": "Month"},
        "conditions": [{
          "conditionType": "Text",
          "description": "Beschikbare spaarpremie voor opbouw pensioenkapitaal. Werkgeversbijdrage 21,5%, werknemersbijdrage 5,5%."
        }]
      },
      {
        "lineId": {"value": "PENSION_PARTNER_RISICO"},
        "amount": {"value": 1.313, "unitCode": "Percentage"},
        "interval": {"value": 1, "unitCode": "Year"},
        "conditions": [{
          "conditionType": "Text",
          "description": "Partnerpensioen op risicobasis dat ingaat bij overlijden tijdens deelnemerschap"
        }]
      },
      {
        "lineId": {"value": "PENSION_WEZEN_RISICO"},
        "amount": {"value": 0.263, "unitCode": "Percentage"},
        "interval": {"value": 1, "unitCode": "Year"},
        "conditions": [{
          "conditionType": "Text",
          "description": "Wezenpensioen op risicobasis voor kinderen"
        }]
      }
    ],
    "franchise": {
      "description": "Franchise € 17.545 (2024), jaarlijks aangepast conform wettelijk minimum"
    },
    "description": "Pensioenrichtleeftijd 68 jaar. Flexibilisering mogelijk (vervroeging/uitstel, deeltijdpensionering)."
  }]
}
```

### Example 3: Metalektro CAO (Minimal Info)

**Dutch CAO Text**:
> "Deelname aan bedrijfstakpensioenfonds verplicht volgens AVV."

**Correct SETU v2.0 Structure**:
```json
{
  "pension": [{
    "name": "Bedrijfstakpensioenfonds Metalektro",
    "origin": {"type": "CollectiveLabourAgreementExtended"},
    "description": "Deelname verplicht volgens Algemeen Verbindend Verklaarde CAO"
  }]
}
```

## Common Mistakes & Fixes

### Mistake 1: Using `pensionFundName` instead of `name`

❌ **WRONG**:
```json
{
  "pension": [{
    "pensionFundName": "Pensioenfonds Zorg en Welzijn"
  }]
}
```

✅ **CORRECT**:
```json
{
  "pension": [{
    "name": "Pensioenfonds Zorg en Welzijn",
    "origin": {"type": "CollectiveLabourAgreement"}
  }]
}
```

### Mistake 2: Separate contribution objects instead of `line[]`

❌ **WRONG**:
```json
{
  "pension": [{
    "name": "Pensioenfonds",
    "employerContribution": {"percentage": 60},
    "employeeContribution": {"percentage": 40}
  }]
}
```

✅ **CORRECT**:
```json
{
  "pension": [{
    "name": "Pensioenfonds",
    "origin": {"type": "CollectiveLabourAgreement"},
    "line": [
      {
        "lineId": {"value": "EMPLOYER_CONTRIBUTION"},
        "amount": {"value": 60, "unitCode": "Percentage"}
      },
      {
        "lineId": {"value": "EMPLOYEE_CONTRIBUTION"},
        "amount": {"value": 40, "unitCode": "Percentage"}
      }
    ]
  }]
}
```

### Mistake 3: Missing required `origin` field

❌ **WRONG**:
```json
{
  "pension": [{
    "name": "Pensioenfonds Zorg en Welzijn"
  }]
}
```

✅ **CORRECT**:
```json
{
  "pension": [{
    "name": "Pensioenfonds Zorg en Welzijn",
    "origin": {"type": "CollectiveLabourAgreement"}
  }]
}
```

## Field Mapping Table

| CAO Dutch Term | SETU v2.0 Field | Example Value |
|----------------|-----------------|---------------|
| Pensioenfonds naam | `name` | `"Pensioenfonds Zorg en Welzijn"` |
| CAO-regeling | `origin.type` | `"CollectiveLabourAgreement"` |
| Werkgeversbijdrage | `line[].amount` (lineId: EMPLOYER_CONTRIBUTION) | `{"value": 60, "unitCode": "Percentage"}` |
| Werknemersbijdrage | `line[].amount` (lineId: EMPLOYEE_CONTRIBUTION) | `{"value": 40, "unitCode": "Percentage"}` |
| Franchise | `franchise.description` | `"Franchise € 17.545 (2024)"` |
| Partnerpensioen | `line[].amount` (lineId: PENSION_PARTNER_RISICO) | `{"value": 1.313, "unitCode": "Percentage"}` |
| Wezenpensioen | `line[].amount` (lineId: PENSION_WEZEN_RISICO) | `{"value": 0.263, "unitCode": "Percentage"}` |
| Pensioenrichtleeftijd | `description` | `"Pensioenrichtleeftijd 68 jaar"` |
| Ingangsdatum | `effectivePeriod.validFrom` | `"2024-01-01"` |
| Einddatum | `effectivePeriod.validTo` | `"2025-12-31"` |

## Validation Checklist

Before finalizing any pension extraction, verify:

- [ ] Field `name` exists and contains pension fund/arrangement name
- [ ] Field `origin` exists with `{"type": "CollectiveLabourAgreement"}`
- [ ] If contributions mentioned, they are in `line[]` array
- [ ] NO custom fields: `pensionFundName`, `employerContribution`, `employeeContribution`
- [ ] NO invalid fields: `pensionScheme`, `pensionSchemeType`, `pensionAge`
- [ ] If franchise mentioned, it's in `franchise.description`
- [ ] If period mentioned, it's in `effectivePeriod`

## Testing Valid Structure

Quick test to verify pension structure is valid:

```bash
# Check pension keys
jq '.pension[0] | keys' output.setu.json

# Expected output (valid):
# ["description", "effectivePeriod", "franchise", "line", "name", "origin"]

# Should NOT contain:
# ["employeeContribution", "employerContribution", "pensionFundName"]
```

## References

- **Official Schema**: `src/cao_engine/models/setu_v2.0.0_official_schemas.json` → `PensionArrangement`
- **Valid Examples**:
  - `data/setu/1055-rabobank-cao-2024-2025-v01102024.gemini-VALID.setu.json`
  - `data/setu/315-metalektro-cao-01-06-2024-tm-31-12-2025-v11122024.gemini-VALID.setu.json`
- **SETU Standard**: [setu-standards/xml-specifications](https://github.com/setu-standards/xml-specifications/tree/main/setu-gelijkwaardige-beloning/v2.0)

## Pipeline Integration

This guide is integrated into the extraction pipeline at 3 levels:

1. **Primary Extraction** (`gemini_primary.py`): Gemini receives explicit pension structure instructions
2. **Review** (`mistral_reviewer.py`): Mistral validates pension structure against checklist
3. **Normalization** (`hybrid_pipeline_mistral.py`): Automatic transformation of legacy fields to SETU v2.0 format

This ensures pension extractions are ALWAYS compliant, even if an LLM makes a mistake.
