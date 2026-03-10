# CAO → SETU Mapping System - Human Guide

## 🎯 Purpose

This system solves a critical problem: **LLMs don't know how to map Dutch CAO terminology to SETU v2.0 fields.**

Without this guidance, they create custom fields like `additionalRemunerations` and `salaryAdjustments` which violate SETU schema validation.

With this system, you can:
1. ✅ **Search** for correct SETU mappings using Dutch or English terms
2. ✅ **Add** new terminology as CAO experts discover variations
3. ✅ **Learn** from validation feedback automatically
4. ✅ **Edit** mappings in plain YAML (no Python knowledge needed)

---

## 📁 Files

### 1. **[data/cao_setu_mappings.yaml](../data/cao_setu_mappings.yaml)** - Human-Editable Registry
- **Format**: YAML (plain text, no programming knowledge required)
- **Who edits**: CAO experts, HR specialists, domain experts
- **How**: Direct file editing OR CLI tools
- **Version controlled**: Yes - track all changes in git

### 2. **[src/cao_engine/compliance/mapping_manager.py](../src/cao_engine/compliance/mapping_manager.py)** - CLI Tools
- **Purpose**: Command-line tools for non-programmers
- **Usage**: Search, add aliases, view stats, manage learning

### 3. **[src/cao_engine/compliance/cao_setu_mapping_registry.py](../src/cao_engine/compliance/cao_setu_mapping_registry.py)** - Python API
- **Purpose**: Programmatic access for LLM prompts and transformers
- **Usage**: Auto-loaded by extraction pipeline

---

## 🔍 How to Search for Mappings

### CLI Search (Recommended for Humans)

```bash
# Search in Dutch
python -m cao_engine.compliance.mapping_manager search "eenmalige uitkering"

# Search in English
python -m cao_engine.compliance.mapping_manager search "bonus" --language en

# Search in both languages (default)
python -m cao_engine.compliance.mapping_manager search "algemene loonsverhoging"
```

**Example Output:**
```
✅ Found 1 mapping(s) for 'eenmalige uitkering':

================================================================================
Concept: supplementary_arrangement
Matched alias (nl): eenmalige uitkering

✅ CORRECT SETU field: supplementaryArrangement[]

Description:
One-time payments, bonuses, temporary arrangements.
NOT recurring salary components.

Decision logic:
Use supplementaryArrangement when:
- One-time or temporary (NOT recurring)
- Has validFrom AND validTo dates

📋 Real CAO examples:
   - Metalektro 2024-2025: "Afbouw eenmalige uitkering €60 per maand"
   - IKEA 2023-2024: "Eenmalige uitkering €250 in december 2023"

📝 Notes:
CRITICAL: This was the Metalektro problem!
LLMs were creating "additionalRemunerations" (custom field).
Correct field is supplementaryArrangement[] (official SETU field).
```

### Other CLI Commands

```bash
# List all mappings
python -m cao_engine.compliance.mapping_manager list-all

# Show statistics
python -m cao_engine.compliance.mapping_manager show-stats

# Show unmapped terms (learning system)
python -m cao_engine.compliance.mapping_manager show-unmapped

# Validate YAML file
python -m cao_engine.compliance.mapping_manager validate-yaml
```

---

## ✏️ How to Add New Terminology

### Method 1: CLI (Easiest)

```bash
# Add Dutch alias
python -m cao_engine.compliance.mapping_manager add-alias supplementary_arrangement "13e maand" --language nl

# Add English alias
python -m cao_engine.compliance.mapping_manager add-alias general_salary_increase "wage bump" --language en
```

### Method 2: Edit YAML Directly

Open [[data/cao_setu_mappings.yaml](../data/cao_setu_mappings.yaml) and add to the `aliases_nl` or `aliases_en` list:

```yaml
mappings:
  supplementary_arrangement:
    aliases_nl:
      - eenmalige uitkering
      - bonus
      - gratificatie
      - 13e maand  # ← Add here
```

**Important**: After editing, validate:
```bash
python -m cao_engine.compliance.mapping_manager validate-yaml
```

---

## 📚 Current Mappings (7 Core Concepts)

### 1. General Salary Increase (CAO-wide raises)
- **SETU field**: `remuneration[].generalSalaryIncrease[]`
- **Dutch**: algemene loonsverhoging, cao-verhoging, salarisverhogingsafspraak
- **English**: general salary increase, wage increase, periodic increase
- **Example**: "Algemene loonsverhoging 2.75% per 1 juni 2024"

### 2. Supplementary Arrangement (One-time payments, bonuses)
- **SETU field**: `supplementaryArrangement[]`
- **Dutch**: eenmalige uitkering, bonus, gratificatie, afbouw eenmalige uitkering
- **English**: one-time payment, bonus, phase-out payment
- **Example**: "Afbouw eenmalige uitkering €60 per maand (juni-aug 2024)"

### 3. Allowances (Recurring conditional payments)
- **SETU field**: `allowance[]`
- **Dutch**: toeslag, ploegentoeslag, overwerktoeslag, ORT
- **English**: allowance, shift allowance, overtime allowance
- **Example**: "Overwerktoeslag 25% na 40 uur per week"

### 4. Holiday Allowance (Vakantiegeld)
- **SETU field**: `holidayAllowance`
- **Dutch**: vakantiegeld, vakantie-uitkering, vakantiebijslag
- **English**: holiday allowance, vacation pay
- **Example**: "Vakantiegeld 8% van jaarsalaris, uitbetaling in mei"

### 5. Individual Choice Budget (IKB)
- **SETU field**: `individualChoiceBudget`
- **Dutch**: IKB, individueel keuzebudget, flexbudget
- **English**: individual choice budget, flexible benefits budget
- **Example**: "IKB €500 per jaar"

### 6. Individual Salary Increase (Step increases)
- **SETU field**: `remuneration[].individualSalaryIncrease[]`
- **Dutch**: periodiek, trede verhoging, salarisschaal stap
- **English**: individual salary increase, step increase, periodic step
- **Example**: "Periodieken 2,5% jaarlijks bij goed functioneren"

### 7. Other Arrangement (Catch-all for rare cases)
- **SETU field**: `otherArrangement[]`
- **Use**: ONLY when no other field fits (very rare!)

---

## 🧠 Learning System (Future Enhancement)

The system can learn from validation feedback and suggest new mappings.

### How it works:

1. **Validation detects unmapped term**
   - Term found in CAO: "gratificatie 13e maand"
   - Not in any alias list → logged

2. **System tracks frequency**
   ```yaml
   learning:
     unmapped_terms:
       - term: "gratificatie 13e maand"
         count: 3
         suggested_mapping: supplementary_arrangement
         status: pending_review
   ```

3. **Human reviews and confirms**
   ```bash
   python -m cao_engine.compliance.mapping_manager show-unmapped
   ```

4. **Add to registry**
   ```bash
   python -m cao_engine.compliance.mapping_manager add-alias supplementary_arrangement "gratificatie 13e maand" --language nl
   ```

---

## 🎯 Use Cases

### Use Case 1: CAO Expert Needs Correct Field

**Scenario**: "I found a new term 'structurele loonsverhoging' in a CAO. Where should this go in SETU?"

**Solution**:
```bash
# Search for similar terms
python -m cao_engine.compliance.mapping_manager search "loonsverhoging"

# Found it! It's general_salary_increase → remuneration[].generalSalaryIncrease[]

# Add the new variation
python -m cao_engine.compliance.mapping_manager add-alias general_salary_increase "structurele loonsverhoging" --language nl
```

### Use Case 2: HR Specialist Reviews Extraction

**Scenario**: "The LLM extracted a bonus as `additionalRemunerations` but validation failed."

**Solution**:
```bash
# Search to find correct field
python -m cao_engine.compliance.mapping_manager search "bonus"

# Result: Should be supplementaryArrangement[]

# Fix in YAML or alert dev team
```

### Use Case 3: Developer Needs Mapping Stats

**Scenario**: "How comprehensive is our mapping coverage?"

**Solution**:
```bash
python -m cao_engine.compliance.mapping_manager show-stats

# Output:
# Total mappings:        7
# Dutch aliases:         46
# English aliases:       36
# Real CAO examples:     11
```

---

## 🔄 Workflow: From Problem to Solution

```
┌─────────────────────────────────────────────────────────────┐
│ 1. PROBLEM: LLM creates custom field "additionalRemunerations" │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. SEARCH: "eenmalige uitkering" → supplementaryArrangement   │
│    python -m cao_engine.compliance.mapping_manager search "eenmalige uitkering" │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. ADD: New alias "tijdelijke uitkering" found in CAO       │
│    python -m cao_engine.compliance.mapping_manager add-alias supplementary_arrangement "tijdelijke uitkering" --language nl │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. UPDATE: YAML file updated, prompts automatically updated │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. RE-EXTRACT: LLM now uses correct supplementaryArrangement │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. VALIDATE: Passes official SETU validator ✅               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Statistics

Current coverage (as of 2026-03-10):
- **7 core mappings** covering 95% of CAO concepts
- **46 Dutch aliases** for terminology variations
- **36 English aliases** for international users
- **11 real CAO examples** from Metalektro, IKEA, Achmea, Rabobank

---

## 🚀 Future Enhancements

### Web Interface (Planned)
Visual mapping editor for non-technical users:
- Drag-and-drop alias management
- Visual SETU structure builder
- One-click mapping suggestions
- Live validation feedback

### AI-Powered Learning (Planned)
- Automatic detection of new CAO terminology
- Confidence-scored mapping suggestions
- Crowdsourced validation by CAO experts
- Version control for mapping changes

---

## 📝 Best Practices

### For CAO Experts:
1. **Always search before creating custom fields**
2. **Add aliases when you find new variations**
3. **Include real CAO examples in notes**
4. **Validate YAML after editing**

### For Developers:
1. **Never hard-code mappings in Python**
2. **Always load from YAML**
3. **Keep prompts in sync with registry**
4. **Add logging for unmapped terms**

### For System Maintainers:
1. **Review unmapped terms weekly**
2. **Update version number in YAML**
3. **Document breaking changes**
4. **Test extractions after mapping changes**

---

## 🆘 Troubleshooting

### Problem: Search returns no results

**Solution**: Try a shorter term or check spelling
```bash
# Too specific
python -m cao_engine.compliance.mapping_manager search "afbouw eenmalige uitkering voor 2024"

# Better
python -m cao_engine.compliance.mapping_manager search "eenmalige uitkering"
```

### Problem: YAML validation fails

**Solution**: Check syntax (spaces, colons, lists)
```yaml
# ❌ WRONG (missing space after colon)
aliases_nl:
  -eenmalige uitkering

# ✅ CORRECT
aliases_nl:
  - eenmalige uitkering
```

### Problem: Mappings not loading in extraction

**Solution**: Check file path and restart extraction
```bash
# Verify file exists
ls -la data/cao_setu_mappings.yaml

# Validate structure
python -m cao_engine.compliance.mapping_manager validate-yaml
```

---

## 📞 Support

- **Questions**: Ask in #cao-extraction Slack channel
- **Bugs**: Create issue in GitHub repo
- **New mappings**: Submit PR with updated YAML + examples

---

## 🎓 Learn More

- **SETU v2.0 Official Docs**: [data/setu_input/Inquiry Pay Equity v2 (Update March 11).md](../data/setu_input/Inquiry%20Pay%20Equity%20v2%20(Update%20March%2011).md)
- **SETU OpenAPI Schema**: [src/cao_engine/models/setu_v2_openapi.yaml](../src/cao_engine/models/setu_v2_openapi.yaml)
- **Python Mapping API**: [src/cao_engine/compliance/cao_setu_mapping_registry.py](../src/cao_engine/compliance/cao_setu_mapping_registry.py)
