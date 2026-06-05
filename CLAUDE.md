# CAO Intelligence Engine

## Project Purpose
AI-native platform processing 700+ Dutch CAO (Collective Labour Agreement) PDFs into structured SETU v2.0 data (Release Candidate 1, released March 11, 2026), with a Momenten (Moments) store as ground truth for a notification engine.

**SETU Version**: v2.0.0-rc.1 (official release candidate from [SETU GitHub](https://github.com/setu-standards/xml-specifications/tree/main/setu-gelijkwaardige-beloning/v2.0))
**Official Docs**: [standard.setu.nl/docs/gelijkwaardige-beloning](https://standard.setu.nl/docs/gelijkwaardige-beloning/)
**Validator Platform**: [wijzerbelonen.nl](https://www.wijzerbelonen.nl/)

## Tech Stack
- Python 3.11+, FastAPI, Pydantic v2, Typer CLI
- Mistral OCR 3 (mistral-ocr-latest) for document processing
- Mistral Large for LLM-driven data extraction
- JSON file storage (PostgreSQL planned)
- structlog for logging

## Architecture

### Dual-Store Architecture (CRITICAL)
The system uses TWO SEPARATE data stores that are NEVER merged:

```
┌─────────────────────────────┐      ┌─────────────────────────────┐
│  SETU Beloningsregister     │      │  Statutory References        │
│  (per inlener, per period)  │◄────►│  (global, versioned)         │
│                             │ link │                              │
│  documentId ────────────────┼──────┤► beloningsregisterId         │
│                             │      │                              │
│  18 root properties         │      │  minimumWage (WML)           │
│  36 SETU definitions        │      │  socialInsurancePremiums     │
│  NEVER modified             │      │  fiscalLimits                │
│                             │      │  stateRetirementAge (AOW)    │
│                             │      │  pensionParameters           │
│                             │      │  regulatoryChanges           │
└─────────────────────────────┘      └─────────────────────────────┘
         What inlener OFFERS               What government MANDATES
```

**ROUTING PRINCIPLE: "Store separately, compare at read time, never merge"**
- SETU = what the inlener OFFERS (CAO conditions, salary scales, allowances, leave days)
- Statutory = what the government MANDATES (WML, SV-premies, fiscal limits, AOW age)
- Cross-reference validator compares at read time, flags mismatches, NEVER modifies either document

### 3-LLM Sequential Pipeline (SETU Extraction)
The system uses a sequential 3-LLM pipeline for SETU v2.0 extraction:

```
PDF → Mistral OCR 3 → Markdown
                         ↓
        ┌────────────────┴────────────────┐
        ↓                                 ↓
  GEMINI 2.5 FLASH                  STATUTORY REFS
  (Primary Extractor)               (Manual Curation)
  - 1M context window               - NO AI extraction
  - Extract complete SETU           - Official sources only
  - Fast & cheap                    - Versioned by period
        ↓                                 ↓
  MISTRAL LARGE                     data/statutory/*.json
  (Reviewer)
  - Review Gemini output
  - Find gaps & issues
  - 500K context
        ↓
  MISTRAL SMALL 2506
  (Judge)
  - Compare both outputs
  - Field-by-field decision
  - Transparent reasoning
        ↓
  Final SETU v2.0 + Judge Report
```

**Key Principle**: Gemini extracts first, Mistral reviews, small model judges. Sequential, not parallel.

## Key Conventions
- All models use Pydantic v2 with strict validation
- Decimal for all monetary values (never float)
- Config via pydantic-settings (.env)
- Dutch domain terms preserved in model field names (loongebouw, functiegroep, trede, moment)
- English for code, comments, and variable names
- src/ layout with hatchling build backend

## Running

### Collection Commands (FNV)
- `python -m cao_engine collect-fnv` - **Incremental** scan: checks FNV sitemap for changes, downloads only new PDFs (seconds if nothing changed)
- `python -m cao_engine collect-fnv --full` - **Full** scan: deep-crawls all 1000+ FNV sector pages (~15-20 min)
- `python -m cao_engine collect-fnv --cao-only` - Only download files that look like actual CAO documents (filters out flyers, brochures)

The collector uses `data/raw/.fnv_manifest.json` to track downloaded PDFs and sitemap lastmod dates. First run is always full; subsequent runs are incremental via sitemap diff.

### Triage Commands
- `python -m cao_engine triage-raw` - **Preview** classification of all PDFs in `data/raw/` (dry run, no files moved)
- `python -m cao_engine triage-raw --execute` - **Execute** triage: move non-relevant files to `data/raw/old/`
- `python -m cao_engine triage-raw --limit 10` - Preview only first 10 archive candidates (for testing)

Classifies PDFs by filename into: CAO, Sociaal Plan, Functiehandboek (KEEP) vs Translation, Older Version, Non-Relevant (ARCHIVE). Also detects older versions of the same CAO by parsing FNV naming patterns. Archived files are moved to `data/raw/old/`, never deleted.

### OCR Commands
- `python -m cao_engine process-single <path.pdf>` - OCR one PDF
- `python -m cao_engine process-batch <directory>` - OCR all PDFs in dir

### Extraction Commands

**NEW: 3-LLM Pipeline** (RECOMMENDED)
- `python -m cao_engine extract-setu-pipeline <ocr_file.md> --cao "CAO Name"` - **Complete 3-LLM pipeline**
  - Step 1: Gemini 2.5 Flash (primary extractor, 1M context)
  - Step 2: Mistral Large (reviewer, finds gaps)
  - Step 3: Mistral Small 2506 (judge, compares outputs)
  - Outputs: `data/setu/*.setu.json` + `data/setu_reports/*.judge_report.json`

**OLD: Individual Steps** (for debugging)
- `python -m cao_engine extract-setu <ocr_file.md>` - Old dual-LLM (deprecated)
- `python -m cao_engine extract-statutory <ocr_file.md>` - Statutory extraction (deprecated - use manual curation)
- `python -m cao_engine extract <ocr_file.md>` - Legacy extraction (custom Pydantic models - deprecated)

### Validation Commands
- `python -m cao_engine validate-cross-reference <setu.json>` - Validate SETU ↔ Statutory (7 rules)

### Exception Review Commands
The system includes transparency features: confidence scoring and exception detection. All extractions include `_confidence` scores (0.0-1.0) per field and `_metadata` with overall statistics. Low-confidence fields are flagged as exceptions requiring human review.

- `python -m cao_engine review-exceptions list <setu.json>` - List all exceptions in SETU file
- `python -m cao_engine review-exceptions list <setu.json> --priority high` - Filter by priority (high/medium/low)
- `python -m cao_engine review-exceptions stats <setu.json>` - Show confidence and exception statistics
- `python -m cao_engine review-exceptions stats` - Show stats across all SETU files
- `python -m cao_engine review-exceptions review <setu.json> --reviewer "Name" --email "email@example.com"` - Interactive review session

**Exception Priorities:**
- HIGH = Compliance-critical (must resolve before use)
- MEDIUM = Cost/calculation impact (should resolve soon)
- LOW = Minor variations (can resolve later)

**Confidence Scoring:**
- Every field gets `_{fieldname}_confidence` score
- Overall confidence in `_metadata.confidence`
- Risk patterns detected: "zie bijlage", "inclusief", "conform", "nader te bepalen"
- Interpretations saved to `data/interpretations/` with full audit trail

### Moments Commands
- `python -m cao_engine moments list --cao <name>` - List moments

### API Server
- `uvicorn cao_engine.api.app:app --reload` - API server

## Data Flow
0. **Collection** via `collect-fnv` → PDFs + manifest in `data/raw/`
1. PDFs in `data/raw/` or `data/pilot/`
2. OCR output in `data/ocr/` (.md + .ocr.json)
3. **SETU data** in `data/setu/` (JSON per CAO - what inlener offers)
4. **Statutory data** in `data/statutory/` (JSON per period - government mandates)
5. Structured CAO data in `data/structured/` (JSON - legacy custom models)
6. Extracted moments in `data/momenten/` (JSON per CAO)

## Domain Glossary

### CAO & SETU Terms
- CAO = Collectieve Arbeidsovereenkomst (Collective Labour Agreement)
- SETU = Stichting Elektronische Transacties Uitzendbranche (Dutch staffing industry standard)
- Inlener = Hiring company (customer receiving temporary workers)
- Beloningsregister = Compensation register (SETU InquiryPayEquity document)
- Loongebouw = Wage/salary structure
- Functiegroep = Job classification group
- Schaal = Salary scale
- Trede = Step within a scale
- Periodeloon = Period salary
- Periodiek = Periodic salary increase (individual step)
- ADV/ATV = Arbeidsduurverkorting (working time reduction)
- Toeslag = Allowance/surcharge
- ORT = Onregelmatigheidstoeslag (irregular hours allowance)
- IKB = Individueel Keuzebudget (individual choice budget)
- Moment = Date-driven trigger/event affecting remuneration

### Statutory Terms
- WML = Wettelijk Minimumloon (statutory minimum wage)
- SV-premies = Sociale verzekeringspremies (social insurance premiums)
- WW = Werkloosheidswet (unemployment insurance)
- ZVW = Zorgverzekeringswet (health insurance)
- WAO/WIA = Work disability insurance
- AOW = Algemene Ouderdomswet (state pension/retirement age)
- WKR = Werkkostenregeling (payroll tax scheme)
- AVV = Algemeen Verbindend Verklaring (general binding declaration)
- StiPP = Stichting Pensioenfonds voor de Personeelsdiensten (sector pension fund)
