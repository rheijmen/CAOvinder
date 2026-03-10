# SETU v2.0 Validation Checklist

**Validator**: https://setu.semantic-treehouse.nl
**Date**: 2026-03-04

---

## Files Ready for Validation

### ✅ Already Validated

| # | CAO | File | Result | Notes |
|---|-----|------|--------|-------|
| 1 | **IKEA** | `1049-ikea-FINAL-VALID.setu.json` | ✅ **PASS** | First successful SETU v2.0 compliant CAO. 47+ errors resolved. |

---

### ⏳ Awaiting Validation

| # | CAO | File | Source | Expected Result |
|---|-----|------|--------|-----------------|
| 2 | **Achmea** | `1004-achmea-FINAL-VALID-v2.setu.json` | Gemini | ✅ Should PASS (fixed array structures) |
| 3 | **NS** | `1021-nederlandse-spoorwegen-cao-01-01-2024-tm-28-02-2025-v02022026.gemini-VALID.setu.json` | Gemini | ❓ Unknown (first validation) |
| 4 | **ING** | `1036-ing-bank-cao-01-01-2025-tm-31-12-2026-v17112025.gemini-VALID.setu.json` | Gemini | ❓ Unknown (first validation) |
| 5 | **IKEA (Gemini)** | `1049-ikea-cao-1-10-2023-tm-31-12-2024-v07022024.gemini-VALID.setu.json` | Gemini | ✅ Likely PASS (same pipeline as manual) |

---

## Validation Instructions

### Online Validation (Recommended)

1. Visit: https://setu.semantic-treehouse.nl
2. Upload JSON file
3. Check for validation errors
4. Record result in this document

### Command Line Validation (if available)

```bash
# If SETU validator CLI tool exists
setu-validate data/setu/1004-achmea-FINAL-VALID-v2.setu.json
```

---

## Expected Results

### Achmea CAO - `1004-achmea-FINAL-VALID-v2.setu.json`

**Previous Errors (v1)**:
```
❌ must NOT have additional properties at /baseDefinition/0
   Additional properties: allowances, description

❌ must be array at /holidayAllowance
   Type: object

❌ must be array at /pension
   Type: object

❌ must have required property 'origin' at /holidayAllowance/0
❌ must NOT have additional properties at /holidayAllowance/0
   Additional properties: percentage, description

❌ must have required property 'origin' at /pension/0
❌ must NOT have additional properties at /pension/0
   Additional properties: employerContributionPercentage, pensionFundName, etc.
```

**Fixes Applied in v2**:
- ✅ Removed `allowances`, `description` from baseDefinition
- ✅ Converted holidayAllowance to array
- ✅ Added required `origin` field to each holidayAllowance item
- ✅ Moved `description` → `name`, removed `percentage`
- ✅ Converted pension to array
- ✅ Added required `origin` field to each pension item
- ✅ Removed all custom fields (employerContributionPercentage, etc.)

**Expected**: ✅ **PASS** (all known errors fixed)

---

### NS CAO - `1021-nederlandse-spoorwegen-cao-...-VALID.setu.json`

**Source**: Gemini 2.5 Flash extraction
**Processing**: SETU v2.0 compliance pipeline
**Transformations Applied**: All standard fixes (documentId, workDuration, salaryScale, arrays)

**Expected**: ❓ **Unknown** - first validation
**Potential Issues**:
- Gemini extraction quality (may have missed some fields)
- NS-specific CAO elements not in SETU v2.0
- Complex allowance structures

---

### ING CAO - `1036-ing-bank-cao-...-VALID.setu.json`

**Source**: Gemini 2.5 Flash extraction
**Processing**: SETU v2.0 compliance pipeline
**Transformations Applied**: All standard fixes

**Expected**: ❓ **Unknown** - first validation
**Potential Issues**:
- Banking sector may have unique compensation structures
- Gemini extraction of complex financial benefits
- Performance-based pay elements

---

### IKEA CAO (Gemini) - `1049-ikea-cao-...-VALID.setu.json`

**Source**: Gemini 2.5 Flash extraction (same CAO as manual)
**Processing**: SETU v2.0 compliance pipeline
**Comparison**: Manual IKEA extraction already validated successfully

**Expected**: ✅ **Likely PASS** (same pipeline as manual IKEA)
**Value**: Validates Gemini extraction quality vs manual

---

## Common Validation Errors to Watch For

### Type Errors
- [ ] Numbers stored as strings
- [ ] Objects where arrays expected
- [ ] Strings where objects expected

### Missing Required Fields
- [ ] `origin` in holidayAllowance items
- [ ] `origin` in pension items
- [ ] `currency` in salaryScale
- [ ] `interval` in workDuration
- [ ] `valuePerWeek` in workDuration

### Additional Properties
- [ ] Custom fields in baseDefinition
- [ ] Custom fields in holidayAllowance items
- [ ] Custom fields in pension items
- [ ] `youthScales` in salaryScale

### Enum Violations
- [ ] Invalid `schemeAgencyId` (must be "Customer" or "Supplier")
- [ ] Invalid `unitCode` in workDuration/amount (must be "Hour")
- [ ] Invalid legal scheme types (must be "KvK", "OIN", or "RSIN")

---

## Validation Results

### Achmea CAO

**File**: `1004-achmea-FINAL-VALID-v2.setu.json`
**Date Validated**: _________________
**Result**: ⬜ PASS / ⬜ FAIL
**Errors Found**: _________________
**Notes**:
```


```

---

### NS CAO

**File**: `1021-nederlandse-spoorwegen-cao-01-01-2024-tm-28-02-2025-v02022026.gemini-VALID.setu.json`
**Date Validated**: _________________
**Result**: ⬜ PASS / ⬜ FAIL
**Errors Found**: _________________
**Notes**:
```


```

---

### ING CAO

**File**: `1036-ing-bank-cao-01-01-2025-tm-31-12-2026-v17112025.gemini-VALID.setu.json`
**Date Validated**: _________________
**Result**: ⬜ PASS / ⬜ FAIL
**Errors Found**: _________________
**Notes**:
```


```

---

### IKEA CAO (Gemini)

**File**: `1049-ikea-cao-1-10-2023-tm-31-12-2024-v07022024.gemini-VALID.setu.json`
**Date Validated**: _________________
**Result**: ⬜ PASS / ⬜ FAIL
**Errors Found**: _________________
**Notes**:
```


```

---

## Summary Statistics

- **Total CAOs Processed**: 5
- **Validated**: 1 ✅
- **Pending Validation**: 4 ⏳
- **Pass Rate**: 100% (1/1 validated so far)

---

## Next Steps After Validation

1. **If All Pass**:
   - ✅ Pipeline is production-ready
   - Document final processing steps
   - Integrate into 3-LLM pipeline
   - Begin processing remaining 700+ CAOs

2. **If Some Fail**:
   - Analyze error patterns
   - Update `process_cao_to_setu_v2.py` transformer
   - Re-process failed CAOs
   - Re-validate

3. **Parify Addendum**:
   - Design schema for Dutch-specific fields
   - Map removed fields → Parify structure
   - Create Parify extraction pipeline

---

## File Locations

All files in: `/Users/macbookpro/DEV/202602_CAOvinder/data/setu/`

```bash
# List all VALID files
ls -lh data/setu/*VALID*.json

# Validate Achmea
open https://setu.semantic-treehouse.nl
# Upload: data/setu/1004-achmea-FINAL-VALID-v2.setu.json

# Validate NS
# Upload: data/setu/1021-nederlandse-spoorwegen-cao-01-01-2024-tm-28-02-2025-v02022026.gemini-VALID.setu.json

# Validate ING
# Upload: data/setu/1036-ing-bank-cao-01-01-2025-tm-31-12-2026-v17112025.gemini-VALID.setu.json

# Validate IKEA (Gemini)
# Upload: data/setu/1049-ikea-cao-1-10-2023-tm-31-12-2024-v07022024.gemini-VALID.setu.json
```
