"""AI/LLM discovery endpoints: llms.txt and llms-full.txt (served at app root, no auth)."""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()

_LLMS_TXT = """# CAO Centraal

> Commercial API for structured Dutch CAO (collective labour agreement) data.

## API
- [OpenAPI specification](/openapi.json): full machine-readable API contract
- [Interactive docs](/docs): Swagger UI

## Key endpoints (require X-API-Key header, prefix /api/v2)
- GET /api/v2/cao/search?company=&sector= : find CAOs
- GET /api/v2/cao/{cao_id} : full canonical SETU document + provenance
- GET /api/v2/cao/{cao_id}/changes?horizon_days= : upcoming changes (vooruitblik)
- GET /api/v2/usage : current usage for your API key
"""

_LLMS_FULL_TXT = _LLMS_TXT + """
## Data model
Each CAO is returned as a canonical SETU v2.0.0-rc.1 document under `document`, plus a
`provenance` object ({status, source, confidence}) describing correctness labeling.
SETU documents are never modified; provenance is joined at read time.

## Authentication
Pass your key in the `X-API-Key` request header. Without a valid key, endpoints return 401.
"""


@router.get("/llms.txt", response_class=PlainTextResponse)
async def llms_txt() -> str:
    return _LLMS_TXT


@router.get("/llms-full.txt", response_class=PlainTextResponse)
async def llms_full_txt() -> str:
    return _LLMS_FULL_TXT
