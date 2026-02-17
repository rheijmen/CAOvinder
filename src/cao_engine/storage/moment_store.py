"""Moment store - the ground truth for the notification engine.

Stores moments per CAO as separate JSON files in data/momenten/.
Provides query methods for the notification engine to find relevant moments
by date range, category, CAO, or type.
"""

import re
from datetime import date
from pathlib import Path

import structlog

from cao_engine.config import Settings
from cao_engine.models.momenten import Moment, MomentCategorie, MomentenSet, MomentType

logger = structlog.get_logger(__name__)


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")[:60]


class MomentStore:
    """Persistent store for CAO moments. One JSON file per CAO."""

    def __init__(self, settings: Settings) -> None:
        self._dir = settings.momenten_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, momenten_set: MomentenSet) -> Path:
        """Save all moments for a CAO."""
        slug = _slugify(momenten_set.cao_naam)
        path = self._dir / f"{slug}_momenten.json"
        path.write_text(momenten_set.model_dump_json(indent=2), encoding="utf-8")
        logger.info(
            "Saved moments",
            cao=momenten_set.cao_naam,
            count=momenten_set.count,
            path=str(path),
        )
        return path

    def load(self, cao_naam: str) -> MomentenSet | None:
        """Load moments for a specific CAO."""
        slug = _slugify(cao_naam)
        path = self._dir / f"{slug}_momenten.json"
        if not path.exists():
            return None
        return MomentenSet.model_validate_json(path.read_text(encoding="utf-8"))

    def load_all(self) -> list[MomentenSet]:
        """Load moments from all CAOs."""
        results = []
        for path in sorted(self._dir.glob("*_momenten.json")):
            ms = MomentenSet.model_validate_json(path.read_text(encoding="utf-8"))
            results.append(ms)
        return results

    def list_caos(self) -> list[str]:
        """List all CAO names that have stored moments."""
        results = []
        for path in sorted(self._dir.glob("*_momenten.json")):
            ms = MomentenSet.model_validate_json(path.read_text(encoding="utf-8"))
            results.append(ms.cao_naam)
        return results

    # --- Query methods for the notification engine ---

    def query_by_date_range(
        self, start: date, end: date, cao_naam: str | None = None
    ) -> list[Moment]:
        """Find all moments within a date range, optionally filtered by CAO."""
        moments: list[Moment] = []
        sets = [self.load(cao_naam)] if cao_naam else self.load_all()
        for ms in sets:
            if ms is not None:
                moments.extend(ms.by_date_range(start, end))
        return sorted(moments, key=lambda m: m.datum or date.max)

    def query_by_categorie(
        self, categorie: MomentCategorie, cao_naam: str | None = None
    ) -> list[Moment]:
        """Find all moments of a specific category."""
        moments: list[Moment] = []
        sets = [self.load(cao_naam)] if cao_naam else self.load_all()
        for ms in sets:
            if ms is not None:
                moments.extend(ms.by_categorie(categorie))
        return moments

    def query_by_type(
        self, moment_type: MomentType, cao_naam: str | None = None
    ) -> list[Moment]:
        """Find all moments of a specific type."""
        moments: list[Moment] = []
        sets = [self.load(cao_naam)] if cao_naam else self.load_all()
        for ms in sets:
            if ms is not None:
                moments.extend(m for m in ms.momenten if m.type == moment_type)
        return moments

    def query_upcoming(
        self, days_ahead: int = 30, cao_naam: str | None = None
    ) -> list[Moment]:
        """Find all moments occurring in the next N days."""
        today = date.today()
        from datetime import timedelta

        end = today + timedelta(days=days_ahead)
        return self.query_by_date_range(today, end, cao_naam)
