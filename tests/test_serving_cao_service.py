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


def test_get_cao_rejects_path_traversal(service: CAOService):
    with pytest.raises(CAONotFoundError):
        service.get_cao("../../etc/passwd")
