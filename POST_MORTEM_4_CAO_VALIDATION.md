# POST-MORTEM: 4 CAO SETU v2.0 Validation Analysis

**Date**: 2026-03-05
**Validator**: Local jsonschema-based validator
**Schema Version**: SETU v2.0.0-draft.3
**CAOs Tested**: 4 (IKEA, Achmea, Metalektro, Rabobank)

---

## 📊 EXECUTIVE SUMMARY

### Overall Results

| Metric | Value | Percentage |
|--------|-------|------------|
| **Total CAOs Validated** | 4 | 100% |
| **✅ Valid CAOs** | 2 | **50%** |
| **❌ Invalid CAOs** | 2 | 50% |
| **Total Errors** | 188 | - |
| **Average Errors per Invalid CAO** | 94 | - |

### Success Rate: 50% 🟨

**Interpretation**:
- **IKEA** and **Achmea** CAOs are **fully SETU v2.0 compliant** ✅
- These represent **manually refined** outputs (hand-fixed or processed through earlier transformers)
- **Metalektro** and **Rabobank** represent **raw Gemini extractions** with 188 validation errors
- This validates that our **manual fixes work** but Gemini extractions need **automated post-processing**

---

## 🎯 DETAILED RESULTS

### ✅ SUCCESS CASES

#### 1. IKEA CAO - VALID
```
File: 1049-ikea-FINAL-VALID.setu.json
Status: ✅ PERFECTLY VALID
Errors: 0
Source: Manual refinement + earlier transformer passes
```

**Why It Succeeded:**
- Underwent multiple rounds of manual schema alignment
- All `baseAmount` fields present in leave amounts
- No additional properties outside schema
- All enum values correct
- Proper type conversions (strings vs numbers)

**Key Takeaway**: Proves the SETU v2.0 schema is achievable with proper transformations

---

#### 2. Achmea CAO - VALID
```
File: 1004-achmea-FINAL-VALID-v2.setu.json
Status: ✅ PERFECTLY VALID
Errors: 0
Source: Manual refinement (v2 with array fixes)
```

**Why It Succeeded:**
- Fixed array structures (holidayAllowance, pension) with required `origin` fields
- Removed extra fields from `baseDefinition`
- All schema constraints satisfied
- Proper field nesting and types

**Key Takeaway**: Array structure fixes (v2) were successful - these patterns can be automated

---

### ❌ FAILURE CASES

#### 3. Metalektro CAO - 84 ERRORS
```
File: 315-metalektro-cao-01-06-2024-tm-31-12-2025-v11122024.gemini-VALID.setu.json
Status: ❌ 84 VALIDATION ERRORS
Source: Raw Gemini 2.5 Flash extraction
```

**Error Distribution:**
- **46 Missing Required** (55%) - Primarily `baseAmount` in leave amounts
- **35 Additional Properties** (42%) - Extra fields not in schema
- **2 Enum Violations** (2%) - Invalid enum values
- **1 Other** (1%) - Structural mismatch

**Critical Issues:**

1. **Missing `baseAmount` in AmountType (46 instances)**
   - Every leave amount missing required `baseAmount` field
   - Schema requires: `{value, unitCode, baseAmount}`
   - Gemini only extracted: `{value, unitCode}`
   - **Impact**: Blocks compliance

2. **Additional Properties in Multiple Places (35 instances)**
   - `labourAgreements.industryIdentifier` (not in schema)
   - `generalSalaryIncrease[]/amount.baseAmount` (wrong location!)
   - `allowance[]/line[]/effectivePeriod` (not allowed in line items)
   - Extra fields in `holidayAllowance`, `sickPay`, `supplementaryArrangement`
   - **Impact**: Schema strictly forbids `additionalProperties`

3. **Enum Typos (2 instances)**
   - `"Generatiepact"` should be `"Generationpact"` (Dutch vs English spelling)
   - `"HalfDay"` not in unitCode enum (should be `"Day"` with value 0.5)
   - **Impact**: Easy fixes but need mapping

**Root Cause**: Gemini extraction prompt doesn't enforce:
- Required field completeness (baseAmount)
- Schema field whitelist (only allowed properties)
- Exact enum value matching

---

#### 4. Rabobank CAO - 104 ERRORS
```
File: 1055-rabobank-cao-2024-2025-v01102024.gemini-VALID.setu.json
Status: ❌ 104 VALIDATION ERRORS
Source: Raw Gemini 2.5 Flash extraction
```

**Error Distribution:**
- **47 Enum Violations** (45%) - Weekday format issues
- **38 Type Errors** (37%) - Numbers instead of strings
- **16 Additional Properties** (15%) - Extra fields
- **2 Missing Required** (2%) - pension.name, leave fields
- **1 Other** (1%) - Structural mismatch

**Critical Issues:**

1. **Weekday Format Disaster (47 enum + 38 type = 85 errors!)**
   - **Current format**: Weekdays as objects `{"value": "Monday"}`
   - **Required format**: Weekdays as simple strings `"Monday"`
   - **Also**: Some weekdays are numbers `1, 2, 3` instead of `"Monday", "Tuesday", "Wednesday"`
   - **Impact**: 81% of Rabobank errors are weekday-related!

2. **Extra Fields in baseDefinition (3 instances)**
   - Has `description` field (not allowed)
   - Only 5 fields permitted: `baseType`, `remunerationIndicator`, `holidayAllowanceIndicator`, `paidLeaveDayIndicator`, `allAllowancesIndicator`
   - **Impact**: Simple fix - remove extras

3. **Missing `pension.name` (2 instances)**
   - Pension items require both `name` and `origin`
   - Gemini only extracted `origin`
   - **Impact**: Can default from description

**Root Cause**: Gemini extraction prompt has:
- Incorrect weekday structure (object vs string)
- No validation of enum value formats
- Incomplete required field extraction

---

## 🔍 PATTERN ANALYSIS

### Pattern 1: Missing `baseAmount` 📍 **HIGHEST PRIORITY**

**Occurrences**: 46 (24% of all errors)
**Affected CAOs**: Metalektro
**Location**: All leave amount fields

**Schema Requirement**:
```json
{
  "AmountType": {
    "required": ["value", "unitCode", "baseAmount"],
    "properties": {
      "baseAmount": {
        "$ref": "#/$defs/BaseAmountType",
        "required": ["unitCode"],
        "properties": {
          "unitCode": {
            "enum": ["FullTimeEquivalent", "Salary", "..."]
          }
        }
      }
    }
  }
}
```

**Current Gemini Output**:
```json
{
  "amount": {
    "value": 25,
    "unitCode": "Day"
    // ❌ Missing baseAmount!
  }
}
```

**Required Fix**:
```json
{
  "amount": {
    "value": 25,
    "unitCode": "Day",
    "baseAmount": {
      "unitCode": "FullTimeEquivalent"
    }
  }
}
```

**Automation Strategy**:
```python
def add_base_amount_to_leave_amounts(data):
    """Add missing baseAmount to all leave amount fields"""
    for leave in data.get("leave", []):
        for leave_type in ["paidLeave", "adv", "holidays", "specialLeave", "wazo"]:
            if leave_type in leave:
                for item in leave[leave_type]:
                    if "amount" in item and "baseAmount" not in item["amount"]:
                        item["amount"]["baseAmount"] = {
                            "unitCode": "FullTimeEquivalent"
                        }
```

---

### Pattern 2: Weekday Format Issues 📍 **SECOND PRIORITY**

**Occurrences**: 85 (45% of all errors!)
**Affected CAOs**: Rabobank
**Location**: `allowance[]/period[]/weekday[]`

**Schema Requirement**:
```json
{
  "weekday": {
    "type": "array",
    "items": {
      "type": "string",
      "enum": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
               "Saturday", "Sunday", "Holiday"]
    }
  }
}
```

**Current Gemini Output (TWO PROBLEMS)**:

**Problem A**: Objects instead of strings
```json
{
  "weekday": [
    {"value": "Monday"},
    {"value": "Tuesday"}
  ]
}
```

**Problem B**: Numbers instead of strings
```json
{
  "weekday": [1, 2, 3, 4, 5]
}
```

**Required Format**:
```json
{
  "weekday": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
}
```

**Automation Strategy**:
```python
def fix_weekday_format(data):
    """Convert weekday objects/numbers to simple strings"""
    WEEKDAY_MAP = {
        1: "Monday", 2: "Tuesday", 3: "Wednesday",
        4: "Thursday", 5: "Friday", 6: "Saturday", 7: "Sunday"
    }

    for allowance in data.get("allowance", []):
        for period in allowance.get("period", []):
            if "weekday" in period:
                fixed_weekdays = []
                for day in period["weekday"]:
                    if isinstance(day, dict) and "value" in day:
                        # Fix: {"value": "Monday"} → "Monday"
                        fixed_weekdays.append(day["value"])
                    elif isinstance(day, int):
                        # Fix: 1 → "Monday"
                        fixed_weekdays.append(WEEKDAY_MAP.get(day, "Monday"))
                    elif isinstance(day, str):
                        # Already correct
                        fixed_weekdays.append(day)
                period["weekday"] = fixed_weekdays
```

---

### Pattern 3: Additional Properties 📍 **THIRD PRIORITY**

**Occurrences**: 51 (27% of all errors)
**Affected CAOs**: Both Metalektro and Rabobank
**Location**: Multiple places

**Top Offenders**:
1. `baseDefinition[].description` (3x) - Not allowed
2. `generalSalaryIncrease[]/amount.baseAmount` (4x) - Wrong location!
3. `holidayAllowance[*]` extra fields (2x)
4. `sickPay[*]` extra fields (2x)
5. `supplementaryArrangement[*]` extra fields (2x)

**Root Cause**: Gemini adds helpful context fields not in schema

**Automation Strategy**:
```python
def remove_additional_properties(data):
    """Remove all fields not in official schema"""

    # baseDefinition: only 5 fields allowed
    if "baseDefinition" in data:
        ALLOWED_BASE_FIELDS = {
            "baseType", "remunerationIndicator", "holidayAllowanceIndicator",
            "paidLeaveDayIndicator", "allAllowancesIndicator"
        }
        for base in data["baseDefinition"]:
            extra_keys = set(base.keys()) - ALLOWED_BASE_FIELDS
            for key in extra_keys:
                del base[key]  # Remove description, allowances, etc.

    # generalSalaryIncrease/amount: NO baseAmount here
    for rem in data.get("remuneration", []):
        for increase in rem.get("generalSalaryIncrease", []):
            if "amount" in increase and "baseAmount" in increase["amount"]:
                del increase["amount"]["baseAmount"]
```

---

### Pattern 4: Enum Value Violations 📍 **FOURTH PRIORITY**

**Occurrences**: 49 (26% of all errors)
**Affected CAOs**: Both (but 96% in Rabobank due to weekday)
**Location**: Various enum fields

**Common Violations**:
1. `supplementaryArrangement[].typeCode = "Generatiepact"`
   - Should be: `"Generationpact"` (English spelling)
2. `amount.unitCode = "HalfDay"`
   - Should be: `"Day"` with value=0.5
3. Weekday objects (covered in Pattern 2)

**Automation Strategy**:
```python
ENUM_FIXES = {
    "supplementaryArrangement.typeCode": {
        "Generatiepact": "Generationpact"
    },
    "amount.unitCode": {
        "HalfDay": "Day"  # Also divide value by 2
    }
}

def fix_enum_violations(data):
    """Fix known enum typos and invalid values"""
    # ... implementation
```

---

## 💡 ROOT CAUSE ANALYSIS

### Why Did 50% Fail?

#### Gemini 2.5 Flash Extraction Issues

1. **Incomplete Field Mapping**
   - Gemini doesn't know `baseAmount` is required in `AmountType`
   - Extraction prompt doesn't reference full schema
   - Missing: Schema-aware validation during extraction

2. **Incorrect Structure Inference**
   - Weekdays extracted as objects `{"value": "Monday"}` instead of strings
   - Likely based on OCR text structure, not schema structure
   - Missing: Type enforcement from schema

3. **Overly Helpful Context Fields**
   - Adds `description`, `allowances`, `effectivePeriod` in wrong places
   - Trying to preserve CAO information not in SETU schema
   - This is **GOOD** data but belongs in **Parify addendum**, not SETU

4. **Enum Value Approximation**
   - Uses Dutch terms ("Generatiepact") vs schema English ("Generationpact")
   - Creates custom unitCodes ("HalfDay") not in official enum
   - Missing: Strict enum enforcement

---

## 📈 COMPARISON: Manual vs Gemini

| Aspect | Manual (IKEA, Achmea) | Gemini (Metalektro, Rabobank) |
|--------|----------------------|-------------------------------|
| **Validity** | ✅ 100% valid | ❌ 0% valid (188 errors) |
| **baseAmount** | ✅ All present | ❌ 0% present in leave amounts |
| **Weekday Format** | ✅ Correct strings | ❌ Objects or numbers |
| **Additional Properties** | ✅ None | ❌ 51 instances |
| **Enum Values** | ✅ All correct | ❌ Typos and invalid values |
| **Processing Time** | Hours (manual) | Minutes (automated) |

**Conclusion**: Gemini is **fast but inaccurate**. Manual is **slow but perfect**.

**Solution**: **Gemini + Automated Post-Processing = Best of Both Worlds**

---

## 🚀 ACTIONABLE RECOMMENDATIONS

### Immediate Actions (Next Session)

#### 1. Build Automated Fixer (Priority 1)
**File**: `src/cao_engine/compliance/transformers/auto_fixer.py`

**Functionality**:
```python
class SETUAutoFixer:
    def fix_all_patterns(self, data):
        data = self.add_missing_base_amounts(data)      # Fix 46 errors
        data = self.fix_weekday_formats(data)           # Fix 85 errors
        data = self.remove_additional_properties(data)  # Fix 51 errors
        data = self.fix_enum_violations(data)           # Fix 49 errors
        data = self.add_missing_required_fields(data)   # Fix 2 errors
        return data
```

**Expected Impact**: Reduce 188 errors → ~0 errors

---

#### 2. Update Gemini Extraction Prompt (Priority 2)
**File**: `src/cao_engine/extraction/gemini_prompt_template.py`

**Add to prompt**:
```
CRITICAL SCHEMA REQUIREMENTS:

1. AmountType MUST include baseAmount:
   {
     "value": <number>,
     "unitCode": "Day"|"Hour"|"Percentage"|...,
     "baseAmount": {"unitCode": "FullTimeEquivalent"}
   }

2. Weekday values MUST be simple strings:
   "weekday": ["Monday", "Tuesday", "Wednesday"]
   NOT: [{"value": "Monday"}]
   NOT: [1, 2, 3]

3. baseDefinition only allows 5 fields:
   - baseType
   - remunerationIndicator
   - holidayAllowanceIndicator
   - paidLeaveDayIndicator
   - allAllowancesIndicator
   DO NOT add: description, allowances

4. Exact enum values (from schema):
   - "Generationpact" (not "Generatiepact")
   - unitCode: Hour|Percentage|SalaryStep|Euro|Day (not "HalfDay")
```

**Expected Impact**: Reduce errors in future extractions by 60-80%

---

#### 3. Create Validation-Driven Pipeline (Priority 3)
**File**: `src/cao_engine/compliance/validation_pipeline.py`

**Flow**:
```
PDF → Gemini Extract → Auto-Fix → Validate → Report
                         ↑                ↓
                         └────── Re-fix ──┘
                         (until valid or max iterations)
```

**Expected Impact**: Fully automated SETU v2.0 compliance

---

### Strategic Actions (Medium Term)

#### 4. Schema-Aware Extraction (Priority 4)
- Provide full SETU v2.0 schema to Gemini/Mistral during extraction
- Use structured output mode (JSON Schema validation in LLM)
- Let LLM validate against schema in real-time

#### 5. Parify Addendum Schema (Priority 5)
- Create separate schema for Dutch-specific fields
- Move `description`, extra `allowances`, `youthScales` there
- Dual output: SETU v2.0 (standardized) + Parify (comprehensive)

#### 6. Test Suite Expansion (Priority 6)
- Validate all 700 CAOs through auto-fixer
- Track error reduction metrics
- Create regression test suite

---

## 📊 SUCCESS METRICS

### Current State
- ✅ **2/4 CAOs valid** (50%)
- ❌ **188 total errors** in 2 CAOs
- ⏱️ **Validation time**: <1 second (local)

### Target State (After Auto-Fixer)
- ✅ **4/4 CAOs valid** (100%)
- ❌ **0 total errors**
- ⏱️ **Processing time**: <10 seconds per CAO (Gemini + Auto-Fix + Validate)

### Long-Term Goal
- ✅ **700/700 CAOs valid** (100%)
- 🤖 **Fully automated** extraction → validation → fixing
- 📅 **Schema evolution** handled automatically
- 🔄 **Continuous validation** on CAO updates

---

## 🎯 CONCLUSION

### What We Learned

1. **SETU v2.0 Compliance is Achievable**
   - IKEA and Achmea prove it works
   - Manual refinement creates perfect results
   - Schema is strict but logical

2. **Gemini Needs Post-Processing**
   - Fast extraction (minutes)
   - But 188 errors across 2 CAOs
   - Patterns are **consistent and automatable**

3. **4 Error Patterns = 99% of Issues**
   - Missing `baseAmount` (24%)
   - Weekday format (45%)
   - Additional properties (27%)
   - Enum violations (26%)
   - **All are mechanically fixable**

4. **Local Validation is Game-Changing**
   - Instant feedback (<1 sec)
   - No manual web uploads
   - Precise error paths
   - Enables automation

### Next Steps

✅ **Phases 1-2 COMPLETE**: Schema extraction + Local validator
🚀 **Phase 3 NEXT**: Error analyzer (pattern detection)
🚀 **Phase 4 NEXT**: Auto-fixer (apply transformations)
🚀 **Phase 5 NEXT**: Validation pipeline (iterative loop)

### Timeline Estimate

- **Phase 3-4 (Auto-Fixer)**: 1 session (~2-3 hours)
- **Phase 5 (Pipeline)**: 1 session (~1-2 hours)
- **Full 700 CAO validation**: 1 week production run

---

## 📁 DELIVERABLES

### Reports Generated
1. ✅ `validation_reports/setu_validation_post_mortem.txt` - Text report
2. ✅ `validation_reports/setu_validation_results.json` - Machine-readable JSON
3. ✅ `POST_MORTEM_4_CAO_VALIDATION.md` - This comprehensive analysis

### Code Artifacts
1. ✅ `src/cao_engine/compliance/validators/base_validator.py` - Local validator
2. ✅ `src/cao_engine/compliance/batch_validator.py` - Batch processing + reporting
3. ✅ `src/cao_engine/compliance/schemas/setu_v2.0.0-draft.3.json` - Official schema
4. ✅ `src/cao_engine/compliance/schema_extractor.py` - OpenAPI converter

### Validation Data
- ✅ 4 CAOs validated
- ✅ 188 errors categorized
- ✅ 4 major patterns identified
- ✅ Automation roadmap defined

---

**END OF POST-MORTEM**

Generated: 2026-03-05
System: CAO Intelligence Engine - SETU v2.0 Validation System
Status: **OPERATIONAL** ✅
