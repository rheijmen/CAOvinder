import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from cao_engine.serving.provenance import ProvenanceStore


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


def test_unsafe_cao_id_returns_neutral(tmp_path: Path):
    store = ProvenanceStore(tmp_path)
    prov = store.get("../../secret")
    assert prov.status == "unverified"
    assert prov.source == "ai_extracted"


def test_provenance_is_immutable():
    store = ProvenanceStore(Path("/nonexistent"))
    prov = store.get("whatever")
    with pytest.raises(ValidationError):
        prov.status = "verified"
