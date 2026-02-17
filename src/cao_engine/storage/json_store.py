"""JSON file-based storage for CAO documents."""

import re
from pathlib import Path

import structlog

from cao_engine.config import Settings
from cao_engine.models import CAODocument

logger = structlog.get_logger(__name__)


def _slugify(name: str) -> str:
    """Convert a CAO name to a safe filename slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug[:60]


class JSONStore:
    """Simple JSON file-based storage for CAO documents."""

    def __init__(self, settings: Settings) -> None:
        self._dir = settings.structured_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, document: CAODocument) -> Path:
        """Save a CAODocument as a JSON file."""
        slug = _slugify(document.metadata.cao_naam)
        filename = f"{slug}.json"
        path = self._dir / filename
        path.write_text(document.model_dump_json(indent=2), encoding="utf-8")
        logger.info("Saved CAO document", path=str(path), cao=document.metadata.cao_naam)
        return path

    def load(self, path: Path) -> CAODocument:
        """Load a CAODocument from a JSON file."""
        return CAODocument.model_validate_json(path.read_text(encoding="utf-8"))

    def load_by_name(self, cao_naam: str) -> CAODocument | None:
        """Load a CAODocument by CAO name."""
        slug = _slugify(cao_naam)
        path = self._dir / f"{slug}.json"
        if path.exists():
            return self.load(path)
        return None

    def list_documents(self) -> list[Path]:
        """List all stored CAO document files."""
        return sorted(self._dir.glob("*.json"))
