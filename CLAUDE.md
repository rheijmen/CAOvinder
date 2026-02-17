# CAO Intelligence Engine

## Project Purpose
AI-native platform processing 250+ Dutch CAO (Collective Labour Agreement) PDFs into structured SETU v2.0 data, with a Momenten (Moments) store as ground truth for a notification engine.

## Tech Stack
- Python 3.11+, FastAPI, Pydantic v2, Typer CLI
- Mistral OCR 3 (mistral-ocr-latest) for document processing
- Mistral Large for LLM-driven data extraction
- JSON file storage (PostgreSQL planned)
- structlog for logging

## Architecture
Pipeline: PDF Ingest -> Mistral OCR -> LLM Extraction -> Moment Detection -> Validation -> Storage

## Key Conventions
- All models use Pydantic v2 with strict validation
- Decimal for all monetary values (never float)
- Config via pydantic-settings (.env)
- Dutch domain terms preserved in model field names (loongebouw, functiegroep, trede, moment)
- English for code, comments, and variable names
- src/ layout with hatchling build backend

## Running
- `python -m cao_engine process-single <path.pdf>` - OCR one PDF
- `python -m cao_engine process-batch <directory>` - OCR all PDFs in dir
- `python -m cao_engine extract <ocr_file.md>` - Extract structured data
- `python -m cao_engine moments list --cao <name>` - List moments
- `uvicorn cao_engine.api.app:app --reload` - API server

## Data Flow
1. PDFs in `data/raw/` or `data/pilot/`
2. OCR output in `data/ocr/` (.md + .ocr.json)
3. Structured CAO data in `data/structured/` (JSON)
4. Extracted moments in `data/momenten/` (JSON per CAO)

## Domain Glossary
- CAO = Collectieve Arbeidsovereenkomst
- SETU = Stichting Elektronische Transacties Uitzendbranche
- Moment = Date-driven trigger/event affecting remuneration
- Inlenersbeloning = Temporary worker compensation matching
- Loongebouw = Wage/salary structure
- Functiegroep = Job classification group
- Schaal = Salary scale
- Trede = Step within a scale
- Periodeloon = Period salary
- ADV = Arbeidsduurverkorting (working time reduction)
- Toeslag = Allowance/surcharge
- AVV = Algemeen Verbindend Verklaring
- WML = Wettelijk Minimumloon
