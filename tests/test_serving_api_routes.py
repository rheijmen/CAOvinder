import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cao_engine.api.app import app
from cao_engine.api.models.api_key import APIKey
from cao_engine.api.v2 import public_routes
from cao_engine.serving.cao_service import CAOService

_STUB_KEY = APIKey(
    id="test-id",
    customer_id="test-customer",
    name="Test Key",
    key_hash="stub",
    key_prefix="test",
    monthly_limit=50000,
    calls_this_month=0,
)


def _make_svc(tmp_path: Path) -> CAOService:
    setu_dir = tmp_path / "setu"
    setu_dir.mkdir()
    momenten_dir = tmp_path / "momenten"
    momenten_dir.mkdir()
    provenance_dir = tmp_path / "provenance"
    provenance_dir.mkdir()
    (setu_dir / "cao-x.setu.json").write_text(
        json.dumps({
            "documentId": "doc-x", "versionId": "1",
            "customer": {"name": "Bedrijf X"},
            "effectivePeriod": {"validFrom": "2024-01-01", "validTo": "2025-12-31"},
            "remuneration": {"salaryScales": []},
        }),
        encoding="utf-8",
    )
    return CAOService(setu_dir=setu_dir, momenten_dir=momenten_dir, provenance_dir=provenance_dir)


@pytest.fixture
def client_with_data(tmp_path: Path):
    """Client with auth stubbed out (for happy-path and 404 tests)."""
    svc = _make_svc(tmp_path)
    app.dependency_overrides[public_routes.get_cao_service] = lambda: svc
    app.dependency_overrides[public_routes.verify_api_key] = lambda: _STUB_KEY
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_auth(tmp_path: Path):
    """Client with real auth but stubbed service (for 401 test)."""
    svc = _make_svc(tmp_path)
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


def test_get_cao_without_api_key_returns_401(client_no_auth):
    r = client_no_auth.get("/api/v2/cao/cao-x")
    assert r.status_code == 401


def test_changes_feed_returns_real_moments(tmp_path):
    import re
    from datetime import date, timedelta

    setu_dir = tmp_path / "setu"
    setu_dir.mkdir()
    momenten_dir = tmp_path / "momenten"
    momenten_dir.mkdir()
    provenance_dir = tmp_path / "provenance"
    provenance_dir.mkdir()
    (setu_dir / "cao-x.setu.json").write_text(
        json.dumps({"documentId": "d", "customer": {"name": "Bedrijf X"},
                    "effectivePeriod": {}, "remuneration": {}}),
        encoding="utf-8",
    )
    soon = (date.today() + timedelta(days=10)).isoformat()
    slug = re.sub(r"[^a-z0-9]+", "_", "Bedrijf X".lower().strip()).strip("_")[:60]
    (momenten_dir / f"{slug}_momenten.json").write_text(
        '{"cao_naam": "Bedrijf X", "momenten": [{"moment_id": "m1", "cao_naam": "Bedrijf X",'
        ' "categorie": "loon", "type": "loonsverhoging", "datum": "' + soon + '",'
        ' "beschrijving": "loon omhoog", "element": "loon",'
        ' "bron_tekst": "art", "bron_artikel": "art"}]}',
        encoding="utf-8",
    )
    svc = CAOService(setu_dir=setu_dir, momenten_dir=momenten_dir, provenance_dir=provenance_dir)
    app.dependency_overrides[public_routes.get_cao_service] = lambda: svc
    app.dependency_overrides[public_routes.verify_api_key] = lambda: _STUB_KEY
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
