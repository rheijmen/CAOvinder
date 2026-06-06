import json

from cao_engine.provenance.provenance_writer import write_provenance
from cao_engine.serving.provenance import ProvenanceStore


def test_writes_sidecar_with_sections_and_mean_confidence(tmp_path):
    write_provenance("1049-ikea", {"remuneration": 0.8, "pension": 0.6, "leave": None}, tmp_path)
    prov = ProvenanceStore(tmp_path).get("1049-ikea")
    assert prov.source == "inter_model_agreement"
    assert prov.status == "unverified"
    assert prov.sections == {"remuneration": 0.8, "pension": 0.6}  # None dropped
    assert abs(prov.confidence - 0.7) < 1e-9  # mean of measurable sections


def test_skips_test_artifacts(tmp_path):
    write_provenance("test_tiny", {"remuneration": 1.0}, tmp_path)
    assert not (tmp_path / "test_tiny.provenance.json").exists()


def test_all_none_writes_no_confidence(tmp_path):
    write_provenance("1049-ikea", {"leave": None}, tmp_path)
    data = json.loads((tmp_path / "1049-ikea.provenance.json").read_text())
    assert data["confidence"] is None
