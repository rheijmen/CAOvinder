"""Read-only provenance store: joins correctness-labeling to canonical SETU at read time.

Provenance lives in a SIDECAR file per CAO (data/provenance/{cao_id}.provenance.json),
NEVER inside the SETU document (the SETU v2.0.0-rc.1 schema forbids extra properties).
When no sidecar exists yet, a neutral, honest default is returned: the data is
AI-extracted and not human-verified. The write side + pipeline wiring is plan 1a-provenance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field

from cao_engine.serving._paths import is_safe_cao_id

logger = structlog.get_logger(__name__)


class Provenance(BaseModel):
    """Correctness-labeling for a CAO document or component."""

    model_config = ConfigDict(frozen=True)

    status: Literal["verified", "unverified"] = "unverified"
    source: str = Field(default="ai_extracted", description="How the data was produced")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    sections: dict[str, float] | None = Field(
        default=None, description="Per-section inter-model agreement ratios"
    )


NEUTRAL_PROVENANCE = Provenance()


class ProvenanceStore:
    """Reads provenance sidecar files; returns a neutral default when absent or invalid."""

    def __init__(self, provenance_dir: Path) -> None:
        self._dir = provenance_dir

    def get(self, cao_id: str) -> Provenance:
        if not is_safe_cao_id(cao_id):
            logger.warning("Unsafe cao_id rejected", cao_id=cao_id)
            return NEUTRAL_PROVENANCE
        path = self._dir / f"{cao_id}.provenance.json"
        if not path.exists():
            return NEUTRAL_PROVENANCE
        try:
            return Provenance.model_validate_json(path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            logger.warning(
                "Invalid provenance sidecar, using neutral default",
                cao_id=cao_id,
                error=str(exc),
            )
            return NEUTRAL_PROVENANCE
