"""CAOService: the single read-only access point to canonical CAO data for the public API.

Reads SETU documents from setu_dir (files named *.setu.json), joins provenance at read
time, and surfaces upcoming changes from the Momenten store. Decoupled from Settings/env
so it is trivially testable; use CAOService.from_settings() in app wiring.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from cao_engine.models.momenten import MomentenSet
from cao_engine.serving._paths import is_safe_cao_id
from cao_engine.serving.provenance import ProvenanceStore
from cao_engine.storage.moment_store import _slugify

SETU_SUFFIX = ".setu.json"


class CAONotFoundError(Exception):
    """Raised when a requested cao_id has no SETU document."""


class CAOService:
    def __init__(self, setu_dir: Path, momenten_dir: Path, provenance_dir: Path) -> None:
        self._setu_dir = setu_dir
        self._momenten_dir = momenten_dir
        self._provenance = ProvenanceStore(provenance_dir)

    @classmethod
    def from_settings(cls, settings) -> CAOService:
        return cls(
            setu_dir=settings.setu_dir,
            momenten_dir=settings.momenten_dir,
            provenance_dir=settings.data_dir / "provenance",
        )

    def list_cao_ids(self) -> list[str]:
        """All cao_ids that have a SETU document (excludes .tables.json etc.)."""
        return sorted(p.name[: -len(SETU_SUFFIX)] for p in self._setu_dir.glob(f"*{SETU_SUFFIX}"))

    def _path_for(self, cao_id: str) -> Path:
        return self._setu_dir / f"{cao_id}{SETU_SUFFIX}"

    def _load_document(self, cao_id: str) -> dict:
        if not is_safe_cao_id(cao_id):
            raise CAONotFoundError(cao_id)
        path = self._path_for(cao_id)
        if not path.exists():
            raise CAONotFoundError(cao_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def get_cao(self, cao_id: str) -> dict:
        """Coarse-grained: the whole canonical SETU document + provenance, in one operation."""
        document = self._load_document(cao_id)
        provenance = self._provenance.get(cao_id)
        return {
            "id": cao_id,
            "document": document,
            "provenance": provenance.model_dump(),
        }

    def search_caos(self, company: str | None, sector: str | None) -> list[dict]:
        """Search CAOs by company (matches customer.name) or sector (matches cao_id)."""
        results: list[dict] = []
        for cao_id in self.list_cao_ids():
            try:
                doc = self._load_document(cao_id)
            except CAONotFoundError:
                continue
            name = (doc.get("customer") or {}).get("name") or cao_id
            period = doc.get("effectivePeriod") or {}
            match_type: str | None = None
            if company and company.lower() in name.lower():
                match_type = "company"
            elif sector and sector.lower() in cao_id.lower():
                match_type = "sector"
            if match_type:
                results.append({
                    "id": cao_id,
                    "name": name,
                    "effective_from": period.get("validFrom"),
                    "effective_to": period.get("validTo"),
                    "match_type": match_type,
                })
        return results

    def get_upcoming_changes(self, cao_id: str, horizon_days: int = 90) -> list[dict]:
        """Forward-looking change calendar for a CAO, from the Momenten store (the vooruitblik)."""
        doc = self._load_document(cao_id)  # raises CAONotFoundError for unknown cao_id
        name = (doc.get("customer") or {}).get("name") or cao_id
        path = self._momenten_dir / f"{_slugify(name)}_momenten.json"
        if not path.exists():
            return []
        ms = MomentenSet.model_validate_json(path.read_text(encoding="utf-8"))
        horizon = date.today() + timedelta(days=horizon_days)
        out: list[dict] = []
        for m in ms.upcoming():
            if m.datum is None or m.datum > horizon:
                continue
            out.append({
                "id": m.moment_id,
                "cao_id": cao_id,
                "type": m.type.value,
                "description": m.beschrijving,
                "effective_date": m.datum.isoformat(),
                "source_article": m.bron_artikel,
            })
        return out
