"""Write the provenance sidecar from computed inter-model agreement (Fase C)."""
from pathlib import Path

from cao_engine.serving._paths import is_safe_cao_id
from cao_engine.serving.provenance import Provenance


def write_provenance(cao_id: str, sections_agreement: dict, provenance_dir: Path) -> Path | None:
    """Write {cao_id}.provenance.json from per-section agreement. Returns the path,
    or None if skipped (unsafe id or test artifact)."""
    if not is_safe_cao_id(cao_id) or cao_id.startswith("test_"):
        return None
    measured = {k: v for k, v in sections_agreement.items() if v is not None}
    confidence = sum(measured.values()) / len(measured) if measured else None
    prov = Provenance(
        status="unverified",
        source="inter_model_agreement",
        confidence=confidence,
        sections=measured or None,
    )
    provenance_dir.mkdir(parents=True, exist_ok=True)
    path = provenance_dir / f"{cao_id}.provenance.json"
    path.write_text(prov.model_dump_json(indent=2), encoding="utf-8")
    return path
