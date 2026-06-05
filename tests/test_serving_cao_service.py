import json
import re
from datetime import date, timedelta
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


def test_get_cao_rejects_path_traversal(service: CAOService):
    with pytest.raises(CAONotFoundError):
        service.get_cao("../../etc/passwd")


def test_search_by_company_matches_customer_name(service: CAOService):
    results = service.search_caos(company="achmea", sector=None)
    assert len(results) == 1
    assert results[0]["id"] == "1004-achmea-v2"
    assert results[0]["name"] == "Achmea"
    assert results[0]["effective_from"] == "2024-01-01"
    assert results[0]["match_type"] == "company"


def test_search_no_match_returns_empty(service: CAOService):
    assert service.search_caos(company="philips", sector=None) == []


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
