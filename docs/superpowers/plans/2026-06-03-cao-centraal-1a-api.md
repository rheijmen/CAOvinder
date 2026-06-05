# CAO Centraal — Plan 1a-api: Serving-laag + geharde read-only CAO-data-API

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Een echte serving-laag bouwen die het canonieke SETU-document (+ provenance, met neutrale fallback) read-only ontsluit via een geharde v2-API, de demo-databugs fixt, een coarse-grained `GET /api/v2/cao/{cao_id}` toevoegt, de nep-changesfeed vervangt door echte Momenten-data, en `llms.txt` levert.

**Architecture:** Een nieuw `serving`-package isoleert alle datatoegang achter `CAOService` (krijgt `setu_dir`/`momenten_dir`/`provenance_dir` als paden, los van env-vars → goed testbaar). De v2-routes worden dunne handlers die `CAOService` aanroepen i.p.v. inline `json.load`. SETU blijft canoniek/compliant; provenance komt uit een aparte sidecar-store met neutrale fallback (volledige vulling = plan 1a-provenance).

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, pytest + FastAPI TestClient. Bestaande conventies: `src/`-layout, `structlog`, ruff (line-length 100).

**Scope:** Bouwt voort op bestaande `src/cao_engine/api/v2/`. Buiten scope (→ andere plannen): tiers/quota/billing/persistente keys/onboarding (plan 1b), provenance-write + pipeline-wiring + backfill (plan 1a-provenance), MCP-server (apart plan). Auth blijft het bestaande in-memory `verify_api_key`.

**Conventies voor elke taak:** draai `ruff check src tests` schoon; commit-messages in `feat:`/`fix:`/`test:`-stijl.

---

### Task 1: Provenance read-model + read-only store (neutrale fallback)

**Files:**
- Create: `src/cao_engine/serving/__init__.py`
- Create: `src/cao_engine/serving/provenance.py`
- Test: `tests/test_serving_provenance.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_serving_provenance.py
import json
from pathlib import Path

from cao_engine.serving.provenance import Provenance, ProvenanceStore


def test_neutral_fallback_when_no_file(tmp_path: Path):
    store = ProvenanceStore(tmp_path)
    prov = store.get("nonexistent-cao")
    assert prov.status == "unverified"
    assert prov.source == "ai_extracted"
    assert prov.confidence is None


def test_reads_existing_provenance_file(tmp_path: Path):
    (tmp_path / "cao-x.provenance.json").write_text(
        json.dumps({"status": "verified", "source": "human_reviewed", "confidence": 0.92}),
        encoding="utf-8",
    )
    store = ProvenanceStore(tmp_path)
    prov = store.get("cao-x")
    assert prov.status == "verified"
    assert prov.source == "human_reviewed"
    assert prov.confidence == 0.92


def test_corrupt_file_falls_back_to_neutral(tmp_path: Path):
    (tmp_path / "cao-x.provenance.json").write_text("{not valid json", encoding="utf-8")
    store = ProvenanceStore(tmp_path)
    prov = store.get("cao-x")
    assert prov.status == "unverified"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_serving_provenance.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cao_engine.serving'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cao_engine/serving/__init__.py
"""Read-only serving layer for the CAO Centraal public API."""
```

```python
# src/cao_engine/serving/provenance.py
"""Read-only provenance store: joins correctness-labeling to canonical SETU at read time.

Provenance lives in a SIDECAR file per CAO (data/provenance/{cao_id}.provenance.json),
NEVER inside the SETU document (the SETU v2.0.0-rc.1 schema forbids extra properties).
When no sidecar exists yet, a neutral, honest default is returned: the data is
AI-extracted and not human-verified. The write side + pipeline wiring is plan 1a-provenance.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class Provenance(BaseModel):
    """Correctness-labeling for a CAO document or component."""

    status: Literal["verified", "unverified"] = "unverified"
    source: str = Field(default="ai_extracted", description="How the data was produced")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


NEUTRAL_PROVENANCE = Provenance()


class ProvenanceStore:
    """Reads provenance sidecar files; returns a neutral default when absent or invalid."""

    def __init__(self, provenance_dir: Path) -> None:
        self._dir = provenance_dir

    def get(self, cao_id: str) -> Provenance:
        path = self._dir / f"{cao_id}.provenance.json"
        if not path.exists():
            return NEUTRAL_PROVENANCE
        try:
            return Provenance.model_validate_json(path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            logger.warning("Invalid provenance sidecar, using neutral default", cao_id=cao_id, error=str(exc))
            return NEUTRAL_PROVENANCE
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_serving_provenance.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cao_engine/serving/__init__.py src/cao_engine/serving/provenance.py tests/test_serving_provenance.py
git commit -m "feat: read-only provenance store with neutral fallback"
```

---

### Task 2: CAOService — cao_id-resolutie + coarse get_cao (fixt glob/key-bugs)

**Files:**
- Create: `src/cao_engine/serving/cao_service.py`
- Test: `tests/test_serving_cao_service.py`

Achtergrond (bevestigd tegen echte data): SETU-bestanden heten `*.setu.json`; top-level keys zijn `documentId, effectivePeriod, customer, remuneration, versionId, issued, baseDefinition, labourAgreements, positionProfile, holidayAllowance, pension`. Er is GEEN top-level `allowances` en GEEN `versionCode`/`_extraction_metadata`. cao_id = bestandsnaam zónder `.setu.json` (bv. `1004-achmea-FINAL-VALID-v2`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_serving_cao_service.py
import json
from pathlib import Path

import pytest

from cao_engine.serving.cao_service import CAONotFoundError, CAOService


@pytest.fixture
def service(tmp_path: Path) -> CAOService:
    setu_dir = tmp_path / "setu"
    setu_dir.mkdir()
    momenten_dir = tmp_path / "momenten"
    momenten_dir.mkdir()
    provenance_dir = tmp_path / "provenance"
    provenance_dir.mkdir()
    # One real-shaped SETU file
    (setu_dir / "1004-achmea-v2.setu.json").write_text(
        json.dumps({
            "documentId": "doc-1004",
            "versionId": "2",
            "customer": {"name": "Achmea"},
            "effectivePeriod": {"validFrom": "2024-01-01", "validTo": "2025-12-31"},
            "remuneration": {"salaryScales": [{"id": "A"}]},
        }),
        encoding="utf-8",
    )
    # A non-SETU sidecar that must be ignored by listing/glob
    (setu_dir / "1004-achmea-v2.tables.json").write_text("{}", encoding="utf-8")
    return CAOService(setu_dir=setu_dir, momenten_dir=momenten_dir, provenance_dir=provenance_dir)


def test_list_ignores_non_setu_files(service: CAOService):
    ids = service.list_cao_ids()
    assert ids == ["1004-achmea-v2"]  # .tables.json excluded


def test_get_cao_returns_whole_document_plus_provenance(service: CAOService):
    result = service.get_cao("1004-achmea-v2")
    assert result["id"] == "1004-achmea-v2"
    assert result["document"]["documentId"] == "doc-1004"
    assert result["document"]["remuneration"]["salaryScales"] == [{"id": "A"}]
    assert result["provenance"]["status"] == "unverified"
    assert result["provenance"]["source"] == "ai_extracted"


def test_get_cao_unknown_raises(service: CAOService):
    with pytest.raises(CAONotFoundError):
        service.get_cao("does-not-exist")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_serving_cao_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cao_engine.serving.cao_service'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cao_engine/serving/cao_service.py
"""CAOService: the single read-only access point to canonical CAO data for the public API.

Reads SETU documents from setu_dir (files named *.setu.json), joins provenance at read
time, and surfaces upcoming changes from the Momenten store. Decoupled from Settings/env
so it is trivially testable; use CAOService.from_settings() in app wiring.
"""

from __future__ import annotations

import json
from pathlib import Path

from cao_engine.serving.provenance import ProvenanceStore

SETU_SUFFIX = ".setu.json"


class CAONotFoundError(Exception):
    """Raised when a requested cao_id has no SETU document."""


class CAOService:
    def __init__(self, setu_dir: Path, momenten_dir: Path, provenance_dir: Path) -> None:
        self._setu_dir = setu_dir
        self._momenten_dir = momenten_dir
        self._provenance = ProvenanceStore(provenance_dir)

    @classmethod
    def from_settings(cls, settings) -> "CAOService":
        return cls(
            setu_dir=settings.setu_dir,
            momenten_dir=settings.momenten_dir,
            provenance_dir=settings.data_dir / "provenance",
        )

    def list_cao_ids(self) -> list[str]:
        """All cao_ids that have a SETU document (excludes .tables.json etc.)."""
        return sorted(p.name[: -len(SETU_SUFFIX)] for p in self._setu_dir.glob(f"*{SETU_SUFFIX}"))

    def _path_for(self, cao_id: str) -> Path:
        return self._setu_dir / f"{cao_id}{SETU_SUFFIX}"

    def _load_document(self, cao_id: str) -> dict:
        path = self._path_for(cao_id)
        if not path.exists():
            raise CAONotFoundError(cao_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def get_cao(self, cao_id: str) -> dict:
        """Coarse-grained: the whole canonical SETU document + provenance, in one operation."""
        document = self._load_document(cao_id)
        provenance = self._provenance.get(cao_id)
        return {
            "id": cao_id,
            "document": document,
            "provenance": provenance.model_dump(),
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_serving_cao_service.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cao_engine/serving/cao_service.py tests/test_serving_cao_service.py
git commit -m "feat: CAOService with coarse get_cao and correct .setu.json handling"
```

---

### Task 3: CAOService.search_caos (fixt glob, leest customer.name)

**Files:**
- Modify: `src/cao_engine/serving/cao_service.py`
- Test: `tests/test_serving_cao_service.py` (toevoegen)

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_serving_cao_service.py
def test_search_by_company_matches_customer_name(service: CAOService):
    results = service.search_caos(company="achmea", sector=None)
    assert len(results) == 1
    assert results[0]["id"] == "1004-achmea-v2"
    assert results[0]["name"] == "Achmea"
    assert results[0]["effective_from"] == "2024-01-01"
    assert results[0]["match_type"] == "company"


def test_search_no_match_returns_empty(service: CAOService):
    assert service.search_caos(company="philips", sector=None) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_serving_cao_service.py -v`
Expected: FAIL — `AttributeError: 'CAOService' object has no attribute 'search_caos'`

- [ ] **Step 3: Write minimal implementation**

```python
# add method to CAOService in src/cao_engine/serving/cao_service.py
    def search_caos(self, company: str | None, sector: str | None) -> list[dict]:
        """Search CAOs by company (matches customer.name) or sector (matches cao_id)."""
        results: list[dict] = []
        for cao_id in self.list_cao_ids():
            try:
                doc = self._load_document(cao_id)
            except CAONotFoundError:
                continue
            name = (doc.get("customer") or {}).get("name") or cao_id
            period = doc.get("effectivePeriod") or {}
            match_type: str | None = None
            if company and company.lower() in name.lower():
                match_type = "company"
            elif sector and sector.lower() in cao_id.lower():
                match_type = "sector"
            if match_type:
                results.append({
                    "id": cao_id,
                    "name": name,
                    "effective_from": period.get("validFrom"),
                    "effective_to": period.get("validTo"),
                    "match_type": match_type,
                })
        return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_serving_cao_service.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cao_engine/serving/cao_service.py tests/test_serving_cao_service.py
git commit -m "feat: CAOService.search_caos matches on customer.name"
```

---

### Task 4: CAOService.get_upcoming_changes (echte Momenten i.p.v. nepdata)

**Files:**
- Modify: `src/cao_engine/serving/cao_service.py`
- Test: `tests/test_serving_cao_service.py` (toevoegen)

Achtergrond: `MomentStore` (src/cao_engine/storage/moment_store.py) bewaart per CAO een bestand `{slug}_momenten.json` met een `MomentenSet`. De slug is `_slugify(cao_naam)`. We koppelen cao_id → cao_naam via `document.customer.name`, slugificeren dat en lezen het bijbehorende momentenbestand. Moment-velden: `datum`, `type`, `beschrijving`, `bron_artikel`, `moment_id` (zie models/momenten.py).

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_serving_cao_service.py
import re
from datetime import date, timedelta


def _slugify(name: str) -> str:  # mirrors moment_store._slugify
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower().strip())
    return slug.strip("_")[:60]


def test_upcoming_changes_reads_real_moments(service: CAOService, tmp_path: Path):
    soon = (date.today() + timedelta(days=30)).isoformat()
    momenten_dir = tmp_path / "momenten"
    slug = _slugify("Achmea")
    (momenten_dir / f"{slug}_momenten.json").write_text(
        '{"cao_naam": "Achmea", "momenten": [' +
        '{"moment_id": "m1", "cao_naam": "Achmea", "categorie": "loon", "type": "loonsverhoging",' +
        f' "datum": "{soon}", "beschrijving": "2.5% verhoging", "element": "loon",' +
        ' "bron_tekst": "Artikel 5", "bron_artikel": "Artikel 5"}]}',
        encoding="utf-8",
    )
    changes = service.get_upcoming_changes("1004-achmea-v2", horizon_days=90)
    assert len(changes) == 1
    assert changes[0]["cao_id"] == "1004-achmea-v2"
    assert changes[0]["type"] == "loonsverhoging"
    assert changes[0]["effective_date"] == soon
    assert changes[0]["description"] == "2.5% verhoging"


def test_upcoming_changes_empty_when_no_moments(service: CAOService):
    assert service.get_upcoming_changes("1004-achmea-v2", horizon_days=90) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_serving_cao_service.py -v`
Expected: FAIL — `AttributeError: 'CAOService' object has no attribute 'get_upcoming_changes'`

- [ ] **Step 3: Write minimal implementation**

```python
# add to top imports of src/cao_engine/serving/cao_service.py
from datetime import date, timedelta

from cao_engine.models.momenten import MomentenSet
from cao_engine.storage.moment_store import _slugify
```

```python
# add method to CAOService
    def get_upcoming_changes(self, cao_id: str, horizon_days: int = 90) -> list[dict]:
        """Forward-looking change calendar for a CAO, from the Momenten store (the vooruitblik)."""
        doc = self._load_document(cao_id)  # raises CAONotFoundError for unknown cao_id
        name = (doc.get("customer") or {}).get("name") or cao_id
        path = self._momenten_dir / f"{_slugify(name)}_momenten.json"
        if not path.exists():
            return []
        ms = MomentenSet.model_validate_json(path.read_text(encoding="utf-8"))
        horizon = date.today() + timedelta(days=horizon_days)
        out: list[dict] = []
        for m in ms.upcoming():
            if m.datum is None or m.datum > horizon:
                continue
            out.append({
                "id": m.moment_id,
                "cao_id": cao_id,
                "type": m.type.value,
                "description": m.beschrijving,
                "effective_date": m.datum.isoformat(),
                "source_article": m.bron_artikel,
            })
        return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_serving_cao_service.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cao_engine/serving/cao_service.py tests/test_serving_cao_service.py
git commit -m "feat: get_upcoming_changes reads real moments (vooruitblik)"
```

---

### Task 5: Coarse endpoint GET /api/v2/cao/{cao_id} + serving-injectie

**Files:**
- Modify: `src/cao_engine/api/v2/public_routes.py`
- Test: `tests/test_serving_api_routes.py`

Achtergrond: routes gebruiken `get_settings()` (regel 23-24) en `verify_api_key`/`verify_api_key_readonly` (regel 113-126) als dependencies. We voegen een `get_cao_service()`-dependency toe en een nieuw read-only endpoint. Het in-memory `API_KEYS_STORE` maakt op de eerste call automatisch een demo-key aan (regel 63-66) — tests sturen die mee via header `X-API-Key`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_serving_api_routes.py
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cao_engine.api.app import app
from cao_engine.api.v2 import public_routes
from cao_engine.serving.cao_service import CAOService


@pytest.fixture
def client_with_data(tmp_path: Path):
    setu_dir = tmp_path / "setu"; setu_dir.mkdir()
    momenten_dir = tmp_path / "momenten"; momenten_dir.mkdir()
    provenance_dir = tmp_path / "provenance"; provenance_dir.mkdir()
    (setu_dir / "cao-x.setu.json").write_text(
        json.dumps({
            "documentId": "doc-x", "versionId": "1",
            "customer": {"name": "Bedrijf X"},
            "effectivePeriod": {"validFrom": "2024-01-01", "validTo": "2025-12-31"},
            "remuneration": {"salaryScales": []},
        }),
        encoding="utf-8",
    )
    svc = CAOService(setu_dir=setu_dir, momenten_dir=momenten_dir, provenance_dir=provenance_dir)
    app.dependency_overrides[public_routes.get_cao_service] = lambda: svc
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_full_cao_document(client_with_data):
    r = client_with_data.get("/api/v2/cao/cao-x", headers={"X-API-Key": "test"})
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "cao-x"
    assert body["document"]["documentId"] == "doc-x"
    assert body["provenance"]["status"] == "unverified"


def test_get_unknown_cao_returns_404(client_with_data):
    r = client_with_data.get("/api/v2/cao/nope", headers={"X-API-Key": "test"})
    assert r.status_code == 404


def test_get_cao_without_api_key_returns_401(client_with_data):
    r = client_with_data.get("/api/v2/cao/cao-x")
    assert r.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_serving_api_routes.py -v`
Expected: FAIL — `AttributeError: module 'cao_engine.api.v2.public_routes' has no attribute 'get_cao_service'`

- [ ] **Step 3: Write minimal implementation**

```python
# in src/cao_engine/api/v2/public_routes.py
# add import near the top:
from cao_engine.serving.cao_service import CAONotFoundError, CAOService

# add dependency after get_settings() (around line 25):
def get_cao_service() -> CAOService:
    return CAOService.from_settings(Settings())
```

```python
# add new endpoint (place after get_current_cao, ~line 245)
@router.get(
    "/cao/{cao_id}",
    summary="Get the full CAO document",
    description="Returns the complete canonical SETU document for a CAO in one operation, plus provenance.",
    tags=["CAO Data"],
)
async def get_full_cao(
    cao_id: str,
    api_key: APIKey = Depends(verify_api_key),
    service: CAOService = Depends(get_cao_service),
):
    try:
        return service.get_cao(cao_id)
    except CAONotFoundError:
        raise HTTPException(status_code=404, detail=f"CAO {cao_id} not found")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_serving_api_routes.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cao_engine/api/v2/public_routes.py tests/test_serving_api_routes.py
git commit -m "feat: coarse GET /api/v2/cao/{cao_id} via CAOService"
```

---

### Task 6: Vervang nep-/changes/feed door echte Momenten-changes

**Files:**
- Modify: `src/cao_engine/api/v2/public_routes.py` (functie `get_changes_feed`, regel 341-375)
- Test: `tests/test_serving_api_routes.py` (toevoegen)

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_serving_api_routes.py
from datetime import date, timedelta


def test_changes_feed_returns_real_moments(tmp_path, monkeypatch):
    import re
    from cao_engine.api.app import app
    from cao_engine.api.v2 import public_routes
    from cao_engine.serving.cao_service import CAOService

    setu_dir = tmp_path / "setu"; setu_dir.mkdir()
    momenten_dir = tmp_path / "momenten"; momenten_dir.mkdir()
    provenance_dir = tmp_path / "provenance"; provenance_dir.mkdir()
    import json as _json
    (setu_dir / "cao-x.setu.json").write_text(
        _json.dumps({"documentId": "d", "customer": {"name": "Bedrijf X"},
                     "effectivePeriod": {}, "remuneration": {}}),
        encoding="utf-8",
    )
    soon = (date.today() + timedelta(days=10)).isoformat()
    slug = re.sub(r"[^a-z0-9]+", "_", "Bedrijf X".lower().strip()).strip("_")[:60]
    (momenten_dir / f"{slug}_momenten.json").write_text(
        '{"cao_naam": "Bedrijf X", "momenten": [{"moment_id": "m1", "cao_naam": "Bedrijf X",'
        ' "categorie": "loon", "type": "loonsverhoging", "datum": "' + soon + '",'
        ' "beschrijving": "loon omhoog", "element": "loon", "bron_tekst": "art", "bron_artikel": "art"}]}',
        encoding="utf-8",
    )
    svc = CAOService(setu_dir=setu_dir, momenten_dir=momenten_dir, provenance_dir=provenance_dir)
    app.dependency_overrides[public_routes.get_cao_service] = lambda: svc
    try:
        client = TestClient(app)
        r = client.get("/api/v2/cao/cao-x/changes", headers={"X-API-Key": "test"})
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 1
        assert body["changes"][0]["type"] == "loonsverhoging"
        assert body["changes"][0]["effective_date"] == soon
    finally:
        app.dependency_overrides.clear()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_serving_api_routes.py::test_changes_feed_returns_real_moments -v`
Expected: FAIL — 404 (endpoint `/cao/{cao_id}/changes` bestaat nog niet)

- [ ] **Step 3: Write minimal implementation**

Replace the body of `get_changes_feed` (the mock at lines 341-375) with a real per-CAO endpoint. Delete the old `@router.get("/changes/feed")` function entirely and add:

```python
@router.get(
    "/cao/{cao_id}/changes",
    summary="Upcoming changes for a CAO (vooruitblik)",
    description="Forward-looking calendar of upcoming CAO changes, sourced from the Momenten store.",
    tags=["CAO Data"],
)
async def get_cao_changes(
    cao_id: str,
    horizon_days: int = Query(90, ge=1, le=730, description="Look-ahead window in days"),
    api_key: APIKey = Depends(verify_api_key),
    service: CAOService = Depends(get_cao_service),
):
    try:
        changes = service.get_upcoming_changes(cao_id, horizon_days=horizon_days)
    except CAONotFoundError:
        raise HTTPException(status_code=404, detail=f"CAO {cao_id} not found")
    return {"changes": changes, "count": len(changes), "filters": {"horizon_days": horizon_days}}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_serving_api_routes.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cao_engine/api/v2/public_routes.py tests/test_serving_api_routes.py
git commit -m "fix: replace mock changes feed with real Momenten-backed /cao/{id}/changes"
```

---

### Task 7: Fix datavorm-bugs in search & current via CAOService

**Files:**
- Modify: `src/cao_engine/api/v2/public_routes.py` (functies `search_cao` regel 160-203, `get_current_cao` regel 219-244)
- Test: `tests/test_serving_api_routes.py` (toevoegen)

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_serving_api_routes.py
def test_search_uses_customer_name_not_filename(client_with_data):
    r = client_with_data.get("/api/v2/cao/search?company=bedrijf", headers={"X-API-Key": "test"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["results"][0]["name"] == "Bedrijf X"  # was filename stem in the demo bug


def test_current_reports_correct_version_key(client_with_data):
    r = client_with_data.get("/api/v2/cao/cao-x/current", headers={"X-API-Key": "test"})
    assert r.status_code == 200
    assert r.json()["version"] == "1"  # from versionId, not the absent versionCode
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_serving_api_routes.py -k "customer_name or version_key" -v`
Expected: FAIL — search name equals filename stem; version equals fallback "1.0" instead of "1".

- [ ] **Step 3: Write minimal implementation**

Rewrite `search_cao` to delegate to the service:

```python
async def search_cao(
    company: str | None = Query(None, description="Filter by company name", examples=["Philips"]),
    sector: str | None = Query(None, description="Filter by sector/industry", examples=["metalektro"]),
    api_key: APIKey = Depends(verify_api_key),
    service: CAOService = Depends(get_cao_service),
):
    results = service.search_caos(company=company, sector=sector)
    return {"results": results, "count": len(results), "search": {"company": company, "sector": sector}}
```

Rewrite `get_current_cao` to use the service and the correct keys:

```python
async def get_current_cao(
    cao_id: str,
    api_key: APIKey = Depends(verify_api_key),
    service: CAOService = Depends(get_cao_service),
):
    try:
        doc = service.get_cao(cao_id)["document"]
    except CAONotFoundError:
        raise HTTPException(status_code=404, detail=f"CAO {cao_id} not found")
    return {
        "id": cao_id,
        "documentId": doc.get("documentId"),
        "customer": doc.get("customer"),
        "effectivePeriod": doc.get("effectivePeriod"),
        "version": str(doc.get("versionId", "1")),
        "metadata": {},
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_serving_api_routes.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cao_engine/api/v2/public_routes.py tests/test_serving_api_routes.py
git commit -m "fix: search/current use CAOService and correct SETU keys"
```

---

### Task 8: llms.txt / llms-full.txt discovery-endpoints

**Files:**
- Create: `src/cao_engine/api/discovery.py`
- Modify: `src/cao_engine/api/app.py` (router includen)
- Test: `tests/test_discovery_endpoints.py`

Achtergrond: `app.py` (regel 90-102) include't routers. `llms.txt` hoort op app-root (geen `/api/v2`-prefix, geen auth) zodat AI-agents het zonder key kunnen ontdekken. OpenAPI staat default aan op `/openapi.json` (FastAPI) — bevestigd door de test hieronder.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_discovery_endpoints.py
from fastapi.testclient import TestClient

from cao_engine.api.app import app

client = TestClient(app)


def test_openapi_json_available():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert r.json()["info"]["title"] == "CAO Centraal"


def test_llms_txt_served_as_markdown():
    r = client.get("/llms.txt")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert "# CAO Centraal" in r.text
    assert "/openapi.json" in r.text
    assert "/api/v2/cao/" in r.text


def test_llms_full_txt_available():
    r = client.get("/llms-full.txt")
    assert r.status_code == 200
    assert "# CAO Centraal" in r.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_discovery_endpoints.py -v`
Expected: FAIL — `/llms.txt` returns 404.

- [ ] **Step 3: Write minimal implementation**

```python
# src/cao_engine/api/discovery.py
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
```

```python
# in src/cao_engine/api/app.py, add to the router imports block (after line 93) and include it:
from cao_engine.api.discovery import router as discovery_router

app.include_router(discovery_router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_discovery_endpoints.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cao_engine/api/discovery.py src/cao_engine/api/app.py tests/test_discovery_endpoints.py
git commit -m "feat: llms.txt and llms-full.txt discovery endpoints"
```

---

### Task 9: Regressiecheck + ruff + volledige suite

**Files:** geen nieuwe.

- [ ] **Step 1: Run de nieuwe serving/API/discovery-tests samen**

Run: `pytest tests/test_serving_provenance.py tests/test_serving_cao_service.py tests/test_serving_api_routes.py tests/test_discovery_endpoints.py -v`
Expected: all PASS.

- [ ] **Step 2: Draai de bestaande API-tests om regressie te vangen**

Run: `pytest tests/test_api_setu.py tests/test_search_api.py tests/test_api_documentation.py -v`
Expected: PASS, of — als een bestaande test de oude demo-databug/`/changes/feed` aannam — een duidelijke, verwachte mismatch. Pas in dat geval de bestaande test aan op het nieuwe (correcte) gedrag en commit met `test:`-message. Verwijder/ą herschrijf geen test zonder te verifiëren dat het nieuwe gedrag juist is.

- [ ] **Step 3: Lint**

Run: `ruff check src/cao_engine/serving src/cao_engine/api tests`
Expected: no errors (fix waar nodig).

- [ ] **Step 4: Volledige suite (sanity)**

Run: `pytest -q`
Expected: groen (afgezien van reeds bestaande, niet-gerelateerde failures — noteer die expliciet, los ze niet stilzwijgend op binnen dit plan).

- [ ] **Step 5: Commit (indien testaanpassingen)**

```bash
git add tests/
git commit -m "test: align existing API tests with corrected serving behavior"
```

---

## Self-Review (uitgevoerd)

**Spec-dekking (plan 1a-api-scope §3 van de spec):** serving-laag ✓ (Task 1-4), datavorm-bugfixes ✓ (Task 2,3,7), coarse GET ✓ (Task 5), echte changes uit Momenten ✓ (Task 4,6), llms.txt ✓ (Task 8), provenance-veld met neutrale fallback ✓ (Task 1,2,5), contract-tests ✓ (elke task). OpenAPI-bevestiging ✓ (Task 8). Buiten scope (tiers/quota/billing/persistente keys/onboarding, provenance-write+pipeline, MCP) — correct uitgesloten, naar plan 1b / 1a-provenance / MCP-plan.

**Placeholder-scan:** geen TBD/TODO; alle code-stappen bevatten complete code en exacte commando's.

**Type-consistentie:** `CAOService(setu_dir, momenten_dir, provenance_dir)` consistent in Task 2-7; `get_cao_service` dependency consistent in Task 5-7; `Provenance(status, source, confidence)` consistent in Task 1/2; `get_upcoming_changes(cao_id, horizon_days)` consistent in Task 4/6. cao_id-conventie (`*.setu.json` stem zonder suffix) consistent.

**Bekende afhankelijkheid:** het echte vullen van provenance (status="verified"/confidence) komt uit **plan 1a-provenance**; tot dan tonen alle responses neutraal `unverified`/`ai_extracted` — dit is bewust en eerlijk (aansprakelijkheidsschild staat).
