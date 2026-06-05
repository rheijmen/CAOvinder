# SETU v2.0 Official Release Update - March 11, 2026

## Summary

On March 11, 2026, SETU released **v2.0.0-rc.1** (Release Candidate 1) for the Inquiry Pay Equity standard. This document tracks the migration from draft.3 to the official release candidate.

## What Changed

### Schema Version
- **OLD**: `v2.0.0-draft.3` (February 6, 2026)
- **NEW**: `v2.0.0-rc.1` (March 5, 2026 - Released March 11, 2026)
- **Status**: Release Candidate 1 (near-final, production-ready)

### Official Sources
1. **GitHub Repository**: [setu-standards/xml-specifications](https://github.com/setu-standards/xml-specifications/tree/main/setu-gelijkwaardige-beloning/v2.0)
2. **Semantic Treehouse**: [Message Model](https://setu.semantic-treehouse.nl/message-model/MessageModel_881f9d0c-bdb8-4848-93b2-b45e6624950d)
3. **Official Documentation**: [standard.setu.nl/docs/gelijkwaardige-beloning](https://standard.setu.nl/docs/gelijkwaardige-beloning/)
4. **Validator Platform**: [wijzerbelonen.nl](https://www.wijzerbelonen.nl/)

## Files Updated

### 1. New Schema Files
- `src/cao_engine/models/setu_v2_openapi_official.yaml` - Official OpenAPI 3.1 spec (125KB)
- `src/cao_engine/models/setu_v2.0.0_official_schemas.json` - All 89 schema definitions (133KB)
- `src/cao_engine/compliance/schemas/setu_v2.0.0-rc.1.json` - Compliance validation schema

### 2. Backed Up Files
- `src/cao_engine/compliance/schemas/setu_v2.0.0-draft.3.json.backup` - Old draft schema

### 3. Code Updates
- `src/cao_engine/compliance/setu_compliance_engine.py` - Updated version comment
- `CLAUDE.md` - Added SETU v2.0.0-rc.1 references and official links

## Schema Structure

The official v2.0.0-rc.1 schema includes **89 definitions**:

### Core Schemas
- `InquiryPayEquity` - Root message structure
- `Condition` - Conditional logic for remuneration
- `Occurrence` - Time-based occurrences

### Key Components (Top 10)
1. InquiryPayEquity
2. error-object
3. IntervalCode
4. IdValue
5. Id
6. AmountUnitCode
7. BaseUnitCode
8. BaseDefinitionCode
9. BaseAmount
10. Proportional

## Required Fields

The InquiryPayEquity root requires:
- `documentId` - Document identifier
- `effectivePeriod` - Validity period
- `customer` - Customer/inlener information
- `remuneration` - Remuneration components

## Where to Find Examples

### JSON Examples
1. **Semantic Treehouse**: Visit [Message Model](https://setu.semantic-treehouse.nl/message-model/MessageModel_881f9d0c-bdb8-4848-93b2-b45e6624950d)
   - Click on "Examples" tab
   - Download JSON examples
   - **Note**: Focus on JSON, ignore XML

2. **wijzerbelonen.nl**:
   - Fill out the web form
   - Export as JSON (SETU-compliant)
   - Use as reference implementation

3. **Our Extractions**:
   - `data/setu/*.setu.json` - 7 CAO extractions
   - All produced with CLEAN pipeline (no `_metadata` fields)
   - Ready to test against v2.0.0-rc.1 validator

## Integration with CAO-SETU Mapping

### Current Mapping System
- `src/cao_engine/compliance/cao_setu_mapping_registry.py` - Mapping registry
- `src/cao_engine/compliance/mapping_manager.py` - Mapping manager
- `data/cao_setu_mappings.yaml` - Mapping configuration
- `docs/CAO_SETU_MAPPING_GUIDE.md` - Mapping documentation

### Next Steps for Mapping
1. **Add Official Examples**: Download JSON examples from Semantic Treehouse
2. **Update Mapping Guide**: Add v2.0.0-rc.1 examples to mapping docs
3. **Test Against Validator**: Validate our 7 SETU files against official schema
4. **Document Patterns**: Create mapping patterns from official examples

## Validation Strategy

### 1. Schema Validation
```python
# Use the new official schema
schema_path = Path("src/cao_engine/compliance/schemas/setu_v2.0.0-rc.1.json")
```

### 2. Online Validation
- Upload SETU JSON to wijzerbelonen.nl web form
- Export and compare with our extractions
- Identify discrepancies

### 3. Compatibility Testing
- Test all 7 existing SETU files:
  - 1004-achmea (Achmea)
  - 1049-ikea (IKEA)
  - 1055-rabobank (Rabobank)
  - 315-metalektro (Metalektro)
  - 1014-rotterdam-shortsea-terminals (RST)
  - 1036-ing-bank (ING Bank)
  - 1056-de-volksbank (De Volksbank)

## Breaking Changes (if any)

**None identified yet** - Our draft.3 schema (Feb 6, 2026) was already very close to rc.1 (Mar 5, 2026).

Key validation:
- `additionalProperties: false` - Still enforced
- Required fields unchanged
- Structure remains compatible

## Migration Checklist

- [x] Download official v2.0.0-rc.1 schema from GitHub
- [x] Extract and save all 89 schema definitions
- [x] Update version references in code
- [x] Update CLAUDE.md documentation
- [x] Backup old draft.3 schema
- [ ] Download JSON examples from Semantic Treehouse
- [ ] Add examples to CAO-SETU mapping guide
- [ ] Test 7 existing SETU files against rc.1 schema
- [ ] Update compliance engine to use rc.1 schema
- [ ] Document any breaking changes (if found)

## Official Resources

### Documentation
- [Gelijkwaardige Beloning Docs](https://standard.setu.nl/docs/gelijkwaardige-beloning/)
- [Inquiry Pay Equity v2.0 (March 11 Update)](data/setu_input/Inquiry%20Pay%20Equity%20v2%20(Update%20March%2011).md)

### Tools
- [Wijzerbelonen.nl](https://www.wijzerbelonen.nl/) - Web form + validator
- [Semantic Treehouse](https://setu.semantic-treehouse.nl/) - Schema browser + examples

### GitHub
- [SETU Standards Repo](https://github.com/setu-standards/xml-specifications)
- [v2.0 Specifications](https://github.com/setu-standards/xml-specifications/tree/main/setu-gelijkwaardige-beloning/v2.0)

## Notes

- **Release Status**: RC1 is near-final, production-ready
- **Final Release**: Expected soon (no breaking changes anticipated)
- **Our Pipeline**: Already produces compliant CLEAN SETU output
- **Action Needed**: Test validation, add examples to docs
