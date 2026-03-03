# CAO Intelligence Engine

An AI-powered platform for processing Dutch Collective Labour Agreement (CAO) documents into structured SETU v2.0 data.

## Project Status

**Current State**: Basic infrastructure is in place, processing pipeline needs refinement

- ✅ 563 CAO PDFs collected from FNV
- ✅ OCR pipeline working (13 documents processed)
- ✅ Backend API server operational
- ✅ Frontend admin dashboard running
- ⚠️ 3-LLM extraction pipeline has JSON parsing issues
- 📝 Only 1 SETU document fully extracted so far

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- API keys for: Google Gemini, Mistral AI

### Setup
```bash
# Install Python dependencies
pip install -e .

# Install frontend dependencies
cd cao-admin
npm install
cd ..

# Copy environment variables
cp .env.example .env
# Edit .env and add your API keys
```

### Running the System

#### 1. Start the Backend API
```bash
uvicorn cao_engine.api.app:app --reload
# API will be available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

#### 2. Start the Frontend Dashboard
```bash
cd cao-admin
npm run dev
# Dashboard will be available at http://localhost:3000
```

## Core Commands

### Collection & Triage
```bash
# Collect CAO PDFs from FNV (incremental scan)
python -m cao_engine collect-fnv

# Full scan of all FNV pages (slow, ~20 min)
python -m cao_engine collect-fnv --full

# Preview which PDFs would be archived
python -m cao_engine triage-raw

# Execute triage (move non-relevant files)
python -m cao_engine triage-raw --execute
```

### Processing Pipeline
```bash
# OCR a single PDF
python -m cao_engine process-single data/raw/example.pdf

# OCR all PDFs in a directory
python -m cao_engine process-batch data/raw/

# Extract SETU data using 3-LLM pipeline
python -m cao_engine extract-setu-pipeline data/ocr/example.md --cao "CAO Name"

# Validate SETU against statutory requirements
python -m cao_engine validate-cross-reference data/setu/example.json
```

### Data Management
```bash
# List extracted moments for a CAO
python -m cao_engine moments list --cao "CAO Name"

# Generate timeline for a CAO
python -m cao_engine generate-timeline --cao "CAO Name"

# Show system status
python -m cao_engine info
```

## Project Structure

```
cao-engine/
├── data/
│   ├── raw/           # Original PDF files (563 files)
│   ├── ocr/           # OCR output (.md + .json)
│   ├── setu/          # Extracted SETU v2.0 documents
│   ├── statutory/     # Government mandates (WML, premiums)
│   └── timelines/     # Generated CAO timelines
├── src/cao_engine/
│   ├── api/           # FastAPI backend
│   ├── extraction/    # LLM extraction pipelines
│   ├── ocr/          # Mistral OCR processing
│   ├── compliance/    # SETU validation engine
│   └── storage/       # Data persistence
├── cao-admin/         # Next.js frontend dashboard
└── tests/            # Test suite

```

## Architecture Overview

### 3-LLM Sequential Pipeline
1. **Gemini 2.5 Flash**: Primary extractor (1M context)
2. **Mistral Large**: Reviews and finds gaps
3. **Mistral Small**: Judges and creates final output

### Data Flow
```
PDF → OCR (Mistral) → Extraction (3-LLM) → SETU JSON → Validation → Dashboard
```

## Known Issues

1. **JSON Parsing**: Gemini sometimes returns invalid JSON (error handling added)
2. **Slow Extraction**: Full pipeline takes 5-10 minutes per document
3. **Limited Test Data**: Only 1 SETU document successfully extracted

## Next Steps

### Immediate (Phase 1)
- [ ] Fix JSON parsing reliability in Gemini extractor
- [ ] Process 5-10 test documents end-to-end
- [ ] Verify dashboard displays extracted data

### Short Term (Phase 2)
- [ ] Simplify pipeline (use only Gemini initially)
- [ ] Add batch processing with queue
- [ ] Improve error recovery

### Long Term (Phase 3)
- [ ] Process all 563 PDFs
- [ ] Add PostgreSQL storage
- [ ] Implement notification engine
- [ ] Deploy to production

## Testing

```bash
# Run basic tests
pytest tests/test_simple.py -v

# Run all tests
pytest

# Frontend tests
cd cao-admin
npm test
```

## API Endpoints

- `GET /health` - Health check
- `GET /api/v1/caos` - List CAO documents
- `GET /api/v1/jobs` - List processing jobs
- `POST /api/v1/caos/upload` - Upload new CAO PDF
- `POST /api/v1/caos/{id}/process` - Start processing

## Environment Variables

Create a `.env` file with:
```
MISTRAL_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
LOG_LEVEL=INFO
```

## Support

For questions or issues, check:
- CLAUDE.md for detailed project conventions
- API docs at http://localhost:8000/docs
- Frontend at http://localhost:3000

## License

Private project - not for distribution