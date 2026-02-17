"""JSON file-based storage for Statutory References.

Statutory references are stored SEPARATELY from SETU documents.
Files are named by effective period: {validFrom}_{validTo}.statutory.json
"""

import json
from datetime import date
from pathlib import Path

import structlog

from cao_engine.config import Settings

logger = structlog.get_logger(__name__)


class StatutoryStore:
    """Simple JSON file-based storage for Statutory References."""

    def __init__(self, settings: Settings) -> None:
        self._dir = settings.data_dir / "statutory"
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, statutory_data: dict) -> Path:
        """Save statutory references as a JSON file.

        Args:
            statutory_data: Dict matching statutory_references_schema.json

        Returns:
            Path to saved file

        File naming: {validFrom}_{validTo}.statutory.json
        Example: 2026-01-01_2026-12-31.statutory.json
        """
        # Extract effective period for filename
        effective_period = statutory_data.get("effectivePeriod", {})
        valid_from = effective_period.get("validFrom", "unknown")
        valid_to = effective_period.get("validTo", "unknown")

        filename = f"{valid_from}_{valid_to}.statutory.json"
        path = self._dir / filename

        path.write_text(json.dumps(statutory_data, indent=2, ensure_ascii=False), encoding="utf-8")

        logger.info(
            "Saved statutory references",
            path=str(path),
            period=f"{valid_from} to {valid_to}",
            has_wml=bool(statutory_data.get("minimumWage")),
            linked_setu=statutory_data.get("beloningsregisterId"),
        )

        return path

    def load(self, path: Path) -> dict:
        """Load statutory references from a JSON file."""
        return json.loads(path.read_text(encoding="utf-8"))

    def load_by_period(self, valid_from: str | date, valid_to: str | date) -> dict | None:
        """Load statutory references by effective period.

        Args:
            valid_from: Start date (ISO string or date object)
            valid_to: End date (ISO string or date object)

        Returns:
            Statutory data dict or None if not found
        """
        # Convert to ISO strings if date objects
        if isinstance(valid_from, date):
            valid_from = valid_from.isoformat()
        if isinstance(valid_to, date):
            valid_to = valid_to.isoformat()

        filename = f"{valid_from}_{valid_to}.statutory.json"
        path = self._dir / filename

        if path.exists():
            return self.load(path)
        return None

    def load_by_setu_id(self, beloningsregister_id: str) -> dict | None:
        """Load statutory references linked to a specific SETU documentId.

        Args:
            beloningsregister_id: SETU documentId.value to search for

        Returns:
            First matching statutory data or None
        """
        for path in self.list_all():
            data = self.load(path)
            if data.get("beloningsregisterId") == beloningsregister_id:
                logger.info(
                    "Found statutory references for SETU document",
                    beloningsregister_id=beloningsregister_id,
                    statutory_file=path.name,
                )
                return data
        return None

    def load_effective_on(self, reference_date: str | date) -> list[dict]:
        """Load all statutory references effective on a specific date.

        Args:
            reference_date: Date to check (ISO string or date object)

        Returns:
            List of statutory data dicts effective on that date
        """
        if isinstance(reference_date, date):
            reference_date = reference_date.isoformat()

        effective_refs = []

        for path in self.list_all():
            data = self.load(path)
            effective_period = data.get("effectivePeriod", {})
            valid_from = effective_period.get("validFrom")
            valid_to = effective_period.get("validTo")

            # Check if reference_date falls within the period
            if valid_from and valid_to:
                if valid_from <= reference_date <= valid_to:
                    effective_refs.append(data)

        logger.info(
            "Found statutory references for date",
            reference_date=reference_date,
            count=len(effective_refs),
        )

        return effective_refs

    def list_all(self) -> list[Path]:
        """List all stored statutory reference files."""
        return sorted(self._dir.glob("*.statutory.json"))

    def list_periods(self) -> list[tuple[str, str]]:
        """List all effective periods in the store.

        Returns:
            List of (validFrom, validTo) tuples
        """
        periods = []
        for path in self.list_all():
            # Parse filename: YYYY-MM-DD_YYYY-MM-DD.statutory.json
            name = path.stem  # Remove .statutory.json
            parts = name.split("_")
            if len(parts) == 2:
                periods.append((parts[0], parts[1]))

        return sorted(periods)
