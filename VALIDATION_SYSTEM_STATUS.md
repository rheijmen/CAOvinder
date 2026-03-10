# SETU v2.0 Local Validation System - Status Report

**Date**: 2026-03-05
**Status**: ✅ **Phase 1 & 2 COMPLETE** - Local validator operational!

---

## 🎯 What We've Built

### ✅ Phase 1: Schema Registry (COMPLETE)
**Files created:**
- `src/cao_engine/compliance/schemas/registry.json` - Version management
- `src/cao_engine/compliance/schemas/setu_v2.0.0-draft.3.json` - Official schema (137KB, 60 definitions)
- `src/cao_engine/compliance/schema_extractor.py` - OpenAPI → JSON Schema converter

**Capabilities:**
- Extracts JSON Schema from OpenAPI 3.1.0 YAML
- Converts `#/components/schemas/` references to `#/$defs/` for jsonschema library
- Analyzes schema: 60 schemas, 6 enums, 40 required field sets, 8 format constraints

### ✅ Phase 2: Local Validator (COMPLETE)
**Files created:**
- `src/cao_engine/compliance/validators/base_validator.py` - Core validation engine

**Capabilities:**
- Validates SETU JSON files locally (NO manual web uploads needed!)
- Uses Python jsonschema library with Draft 2020-12 spec
- Categorizes errors into 6 types:
  1. Additional properties
  2. Missing required fields
  3. Type errors
  4. Enum violations
  5. Format violations
  6. Other validation errors
- Provides JSON paths for every error
- Human-readable error reports

---

## 📊 Validation Results

### Test Run: 3 CAOs

#### ✅ IKEA CAO - VALID!
```
File: 1049-ikea-FINAL-VALID.setu.json
Status: ✅ VALID
Errors: 0
```
**This proves our manual fixes work!**

#### ❌ Metalektro CAO - 84 Errors
```
File: 315-metalektro-cao-01-06-2024-tm-31-12-2025-v11122024.gemini-VALID.setu.json
Total Errors: 84
├─ Additional Properties: 35
│  • labourAgreements.industryIdentifier (not in schema)
│  • labourAgreements.collectiveLabourAgreement.id.schemeAgencyId (not allowed)
│  • generalSalaryIncrease[*]/amount.baseAmount (wrong location)
│  • allowance[11]/line[*].effectivePeriod (not allowed in line)
│  • holidayAllowance[*]/line[*] extra fields
│  • sickPay[*] extra fields
│  • supplementaryArrangement[*] extra fields
│
├─ Missing Required: 46
│  • leave/paidLeave[*]/amount missing baseAmount (9 instances)
│  • leave/adv[*]/amount missing baseAmount (1 instance)
│  • leave/holidays[*]/amount missing baseAmount (7 instances)
│  • leave/specialLeave[*]/amount missing baseAmount (28 instances)
│  • pension[0] missing name
│
├─ Enum Violations: 2
│  • supplementaryArrangement[0].typeCode = "Generatiepact"
│    (should be "Generationpact" - typo!)
│  • otherArrangement[1]/line[0]/amount.unitCode = "HalfDay"
│    (not in enum: Hour, Percentage, SalaryStep, Euro, Day)
│
└─ Other: 1
   • holidayAllowance[0].payDate structure mismatch
```

#### ❌ Rabobank CAO - 104 Errors
```
File: 1055-rabobank-cao-2024-2025-v01102024.gemini-VALID.setu.json
Total Errors: 104
├─ Additional Properties: 16
│  • baseDefinition[*].description (not allowed - only 5 fields permitted)
│  • generalSalaryIncrease[*]/amount.baseAmount (wrong location)
│  • holidayAllowance[*] extra fields
│  • sickPay[*] extra fields
│  • leave[0] extra fields
│  • supplementaryArrangement[*] extra fields
│
├─ Type Errors: 38
│  • allowance[7,10]/period[*]/weekday[*] are numbers, should be strings
│    (e.g., 1 instead of "Monday")
│
├─ Enum Violations: 47
│  • allowance[7,10]/period[*]/weekday[*] not in enum
│    (values are numeric 1-5, should be "Monday", "Tuesday", etc.)
│
├─ Missing Required: 2
│  • pension[0] missing name
│  • leave[0]/specialLeave[6] missing amount and interval
│
└─ Other: 1
   • Structural mismatch
```

---

## 🔍 Error Pattern Analysis

### Pattern 1: Missing `baseAmount` (46 instances in Metalektro)
**Schema requirement:**
```json
{
  "AmountType": {
    "required": ["value", "unitCode", "baseAmount"],
    "properties": {
      "value": {"type": "number"},
      "unitCode": {"$ref": "#/$defs/AmountUnitCodeType"},
      "baseAmount": {"$ref": "#/$defs/BaseAmountType"}
    }
  }
}
```

**Current data:**
```json
{
  "amount": {
    "value": 25,
    "unitCode": "Day"
    // ❌ MISSING: baseAmount
  }
}
```

**Fix needed:**
```json
{
  "amount": {
    "value": 25,
    "unitCode": "Day",
    "baseAmount": {
      "unitCode": "FullTimeEquivalent"  // or "Salary" or other valid value
    }
  }
}
```

**Affected fields:**
- `leave/paidLeave[*]/amount`
- `leave/adv[*]/amount`
- `leave/holidays[*]/amount`
- `leave/specialLeave[*]/amount`

---

### Pattern 2: Weekday Type/Enum Errors (47+38=85 in Rabobank)
**Schema requirement:**
```json
{
  "weekday": {
    "items": {
      "type": "string",
      "enum": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Holiday"]
    }
  }
}
```

**Current data:**
```json
{
  "weekday": [1, 2, 3, 4, 5]  // ❌ Numbers instead of strings
}
```

**Fix needed:**
```json
{
  "weekday": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
}
```

**Mapping:**
- 1 → "Monday"
- 2 → "Tuesday"
- 3 → "Wednesday"
- 4 → "Thursday"
- 5 → "Friday"
- 6 → "Saturday"
- 7 → "Sunday"

---

### Pattern 3: Additional Properties in `baseDefinition` (3 in Rabobank)
**Schema allows ONLY 5 fields:**
- `baseType`
- `remunerationIndicator`
- `holidayAllowanceIndicator`
- `paidLeaveDayIndicator`
- `allAllowancesIndicator`

**Current data has extras:**
```json
{
  "baseType": "Maandbezoldiging",
  "remunerationIndicator": true,
  "holidayAllowanceIndicator": false,
  "paidLeaveDayIndicator": false,
  "allAllowancesIndicator": false,
  "description": "CAO-loon plus toelagen"  // ❌ NOT ALLOWED
}
```

**Fix:** Remove `description` field → move to Parify addendum

---

### Pattern 4: Wrong Location for `baseAmount` in `generalSalaryIncrease`
**Schema for `generalSalaryIncrease/amount`:**
```json
{
  "properties": {
    "amount": {
      "required": ["value", "unitCode"],
      "properties": {
        "value": {"type": "number"},
        "unitCode": {"$ref": "#/$defs/AmountUnitCodeType"}
      }
      // ❌ NO baseAmount here!
    }
  }
}
```

**Current data:**
```json
{
  "generalSalaryIncrease": [{
    "amount": {
      "value": 3.5,
      "unitCode": "Percentage",
      "baseAmount": {...}  // ❌ Additional property!
    }
  }]
}
```

**Fix:** Remove `baseAmount` from `generalSalaryIncrease/amount`

---

### Pattern 5: Missing `pension.name` (2 instances)
**Schema requirement:**
```json
{
  "pension": {
    "items": {
      "required": ["name", "origin"]
    }
  }
}
```

**Current data:**
```json
{
  "pension": [{
    "origin": {"type": "CollectiveLabourAgreement"}
    // ❌ MISSING: name
  }]
}
```

**Fix:**
```json
{
  "pension": [{
    "name": "Pension arrangement",  // Add from description or default
    "origin": {"type": "CollectiveLabourAgreement"}
  }]
}
```

---

### Pattern 6: Enum Typo - "Generatiepact" vs "Generationpact"
**Current:** `"Generatiepact"` (Dutch spelling)
**Required:** `"Generationpact"` (English spelling in enum)

**Fix:** Simple string replacement

---

### Pattern 7: Invalid UnitCode "HalfDay"
**Allowed values:** `["Hour", "Percentage", "SalaryStep", "Euro", "Day"]`
**Current value:** `"HalfDay"`

**Fix:** Convert to `"Day"` with value = 0.5

---

## 🚀 Next Steps

### Phase 3: Error Analyzer (IN PROGRESS)
Create `src/cao_engine/compliance/analyzers/error_analyzer.py` that:
1. Collects all validation errors from multiple CAOs
2. Groups by pattern (e.g., "46 missing baseAmount in leave amounts")
3. Identifies root causes
4. Generates transformation rules

### Phase 4: Auto-Fixer
Create `src/cao_engine/compliance/transformers/auto_fixer.py` that:
1. Adds missing `baseAmount` fields to all leave/allowance amounts
2. Converts weekday numbers → day names
3. Removes `description` from `baseDefinition`
4. Removes `baseAmount` from `generalSalaryIncrease`
5. Adds `name` to pension items
6. Fixes enum typos
7. Converts invalid unitCodes

### Phase 5: Validation Pipeline
Create iterative loop:
```
Validate → Analyze Errors → Generate Fixes → Apply Fixes → Re-validate
```

Repeat until `error_count == 0`

---

## 📈 Progress Metrics

| Metric | Status |
|--------|--------|
| **Schema Extracted** | ✅ 137KB, 60 definitions |
| **Local Validator** | ✅ Working, categorizes 6 error types |
| **CAOs Validated** | 3 (IKEA ✅, Metalektro ❌ 84, Rabobank ❌ 104) |
| **Error Patterns Identified** | 7 major patterns |
| **Automation** | Batch validation ready |
| **Next Milestone** | Error analyzer + auto-fixer |

---

## 🎯 Target Outcome

**Goal:** All 5 CAOs (and eventually all 700+) validate with 0 errors

**Current:**
- ✅ IKEA: 0 errors
- ❌ Metalektro: 84 → 0 (via auto-fixer)
- ❌ Rabobank: 104 → 0 (via auto-fixer)
- ⏳ ING: Not yet validated
- ⏳ Achmea: Not yet validated

**Timeline:**
- Phase 3-4 (Error Analyzer + Auto-Fixer): Next session
- Phase 5 (Pipeline): Next session
- Full 700 CAO validation: Production deployment

---

## 💡 Key Achievements

1. **No more manual web uploads!** Validation is now instant and local
2. **Precise diagnostics**: Exact JSON paths + error types for every issue
3. **Pattern detection**: Clear patterns emerged (baseAmount, weekday, etc.)
4. **Reproducible**: Can validate 100s of CAOs in seconds
5. **Schema versioning ready**: Registry supports future SETU updates
6. **Validation modes**: Can run strict/lenient/production/draft validation

---

## 🔧 Files Created

```
src/cao_engine/compliance/
├── schemas/
│   ├── registry.json                          (Version management)
│   └── setu_v2.0.0-draft.3.json              (Official schema, 137KB)
├── validators/
│   └── base_validator.py                      (Local validation engine)
└── schema_extractor.py                        (OpenAPI converter)
```

---

## 🎉 Summary

**WE NOW HAVE A WORKING LOCAL VALIDATION SYSTEM!**

- Extracts official SETU v2.0 schema from OpenAPI
- Validates any SETU JSON file in milliseconds
- Categorizes errors for pattern analysis
- Ready for AI-powered auto-fixing

The validation-driven development cycle is operational. Next: build the error analyzer and auto-fixer to close the loop.
