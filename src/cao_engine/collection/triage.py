"""CAO PDF Triage — classify files as relevant or archivable.

Classifies PDFs in data/raw/ into:
  - KEEP: actual CAO documents, sociale plannen, functiehandboeken
  - ARCHIVE: translations, older versions, brochures, flyers, reports, etc.

Uses filename-based heuristics. No file is deleted — archived files are moved
to data/raw/old/.
"""

import re
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from rich.console import Console

console = Console()


class FileCategory(str, Enum):
    CAO = "CAO"
    SOCIAAL_PLAN = "Sociaal Plan"
    FUNCTIEHANDBOEK = "Functiehandboek"
    TRANSLATION = "Vertaling"
    OLDER_VERSION = "Oudere versie"
    NON_RELEVANT = "Niet-relevant"


class TriageAction(str, Enum):
    KEEP = "keep"
    ARCHIVE = "archive"


@dataclass
class TriageResult:
    filename: str
    category: FileCategory
    action: TriageAction
    reason: str
    newer_version: str | None = None


# ---------------------------------------------------------------------------
# Classification patterns
# ---------------------------------------------------------------------------

# Filename fragments that indicate a translation
_TRANSLATION_PATTERNS = [
    r"-cla-\d",                       # CLA = Collective Labour Agreement (e.g., cla-2024)
    r"-cla-english",
    r"-cla-for-the-",
    r"-english-",
    r"-engels[-.]",
    r"-engelse-versie",
    r"collective-labour-agreement",
    r"terms-and-conditions.*engels",
    r"-duits-\d",
    r"-pools-\d",
    r"-roemeens-\d",
    r"-oekraiens-\d",
    r"-bulgaars-\d",
    r"-en\.pdf$",                     # filename ends with -en.pdf (English version)
]

# Filename fragments that indicate non-relevant documents
_NON_RELEVANT_PATTERNS = [
    r"brochure",
    r"flyer",
    r"infographic",
    r"krant[je]*[-_]",
    r"nieuwsbrief",
    r"poster",
    r"e-?mailbanner",
    r"witboek",
    r"rapport[-_]",
    r"inspectierapport",
    r"factsheet",
    r"visie-op-",
    r"position-?paper",
    r"adviesrapport",
    r"brandbrief",
    r"petitie",
    r"oproep",
    r"campagne",
    r"enquete",
    r"meldpunt",
    r"aanpakplan",
    r"minimumtarief",
    r"minimum.*zzp",
    r"check-loonstrook",
    r"werkdruk",
    r"loontabel",                      # standalone wage tables (not part of CAO)
    r"toelichting-op-",
    r"uitleg-",
    r"overgangsregeling",
    r"overgangsbepalingen",
    r"overgangsmaatregelen",
    r"principeakkoord",
    r"onderhandelaarsakkoord",
    r"onderhandelresultaat",
    r"onderhandelingsresultaat",
    r"voorstellen(?:brief)?[-_]",
    r"kijk-en-vergelijk",
    r"pensioen(?:overeenkomst|regelment|reglement|cao)",
    r"pensioenfonds",
    r"rvu-regeling",
    r"rvu-reglement",
    r"bijdragefonds",
    r"sociaal-fonds",
    r"suwas",
    r"addendum",
    r"statijdenbrochure",
    r"transitieplan",
    r"vitaliteitsregeling",
    r"tijdspaarregeling",
    r"vrijwillige-vertrek",
    r"arbeidsongeschik",
    r"arbo-",
    r"arbocatalogus",
    r"verwerking-persoonsgegevens",
    r"rooster-consulenten",
    r"transcript",
    r"podcast",
    r"bijlage-verslag",
    r"loga-rapport",
    r"seniorenregeling",
    r"beroepscode",
    r"\.pdf\.aspx$",                    # broken download links
]

# Patterns that strongly indicate a real CAO document
_CAO_PATTERNS = [
    # Standard FNV format: ID-name-cao-startdate-tm-enddate-version.pdf
    r"^\d+-.*-cao-\d{2}-\d{2}-\d{4}-tm-",
    # Simpler: contains "cao" and date range
    r"-cao-\d{4}",
    r"-cao-.*-v\d+",
]

_SOCIAAL_PLAN_PATTERNS = [
    r"sociaal-plan",
    r"sociaal-statuut",
    r"sociale-leidraad",
]

_FUNCTIE_PATTERNS = [
    r"functiehandboek",
    r"functieprofielen",
    r"functieboek",
    r"functiewaardering",
]


def _matches_any(filename: str, patterns: list[str]) -> bool:
    lower = filename.lower()
    return any(re.search(p, lower) for p in patterns)


def classify_file(filename: str) -> TriageResult:
    """Classify a single PDF file by its filename."""
    lower = filename.lower()

    # 1. Translations — always archive
    if _matches_any(filename, _TRANSLATION_PATTERNS):
        # But not if it's also clearly a Dutch CAO (e.g., "cla" in company name)
        if not _matches_any(filename, _CAO_PATTERNS):
            return TriageResult(
                filename=filename,
                category=FileCategory.TRANSLATION,
                action=TriageAction.ARCHIVE,
                reason="Vertaling (niet-Nederlands)",
            )

    # 2. Functiehandboek — keep
    if _matches_any(filename, _FUNCTIE_PATTERNS):
        return TriageResult(
            filename=filename,
            category=FileCategory.FUNCTIEHANDBOEK,
            action=TriageAction.KEEP,
            reason="Functiehandboek/-waardering",
        )

    # 3. Sociaal plan — keep
    if _matches_any(filename, _SOCIAAL_PLAN_PATTERNS):
        return TriageResult(
            filename=filename,
            category=FileCategory.SOCIAAL_PLAN,
            action=TriageAction.KEEP,
            reason="Sociaal plan/statuut",
        )

    # 4. CAO document — keep
    if _matches_any(filename, _CAO_PATTERNS) or "-cao-" in lower:
        return TriageResult(
            filename=filename,
            category=FileCategory.CAO,
            action=TriageAction.KEEP,
            reason="CAO document",
        )

    # 5. Non-relevant patterns — archive
    if _matches_any(filename, _NON_RELEVANT_PATTERNS):
        return TriageResult(
            filename=filename,
            category=FileCategory.NON_RELEVANT,
            action=TriageAction.ARCHIVE,
            reason="Geen CAO/SP/functieboek",
        )

    # 6. Default: if filename starts with a numeric ID, likely a CAO-related doc
    if re.match(r"^\d{2,4}-", filename):
        return TriageResult(
            filename=filename,
            category=FileCategory.CAO,
            action=TriageAction.KEEP,
            reason="Waarschijnlijk CAO-gerelateerd (ID-prefix)",
        )

    # 7. Everything else without an ID prefix is likely non-relevant
    return TriageResult(
        filename=filename,
        category=FileCategory.NON_RELEVANT,
        action=TriageAction.ARCHIVE,
        reason="Geen herkenbaar CAO-bestand",
    )


def find_older_versions(files: list[str]) -> dict[str, str]:
    """Find files that are older versions of another file.

    Detects the FNV naming pattern: {id}-{name}-cao-{startdate}-tm-{enddate}-{version}.pdf
    Groups by ID prefix + name and keeps only the newest version.

    Returns: {old_filename: newer_filename}
    """
    # Group by CAO ID prefix (the leading number)
    groups: dict[str, list[tuple[str, str]]] = {}  # id -> [(filename, version_date)]

    pattern = re.compile(
        r"^(\d+)-(.+?)-cao-(\d{2}-\d{2}-\d{4})-tm-(\d{2}-\d{2}-\d{4})-(v\w+)\.pdf$",
        re.IGNORECASE,
    )

    for f in files:
        m = pattern.match(f)
        if m:
            cao_id = m.group(1)
            name = m.group(2)
            key = f"{cao_id}-{name}"
            version = m.group(5)  # e.g., v06012026
            groups.setdefault(key, []).append((f, version))

    older: dict[str, str] = {}
    for key, versions in groups.items():
        if len(versions) <= 1:
            continue
        # Sort by version string (vDDMMYYYY) — extract date
        def _version_date(v: tuple[str, str]) -> str:
            ver = v[1].lstrip("v").lstrip("best")
            if len(ver) == 8:
                # DDMMYYYY -> YYYYMMDD for sorting
                return ver[4:8] + ver[2:4] + ver[0:2]
            return ver

        sorted_versions = sorted(versions, key=_version_date)
        newest = sorted_versions[-1][0]
        for filename, _ in sorted_versions[:-1]:
            older[filename] = newest

    return older


def triage_directory(
    raw_dir: Path,
    limit: int | None = None,
) -> list[TriageResult]:
    """Classify all PDFs in a directory.

    Args:
        raw_dir: Path to the raw PDF directory.
        limit: If set, only process this many archive candidates (for testing).
    """
    pdfs = sorted(f.name for f in raw_dir.glob("*.pdf"))
    if not pdfs:
        return []

    # First pass: find older versions
    older_versions = find_older_versions(pdfs)

    # Second pass: classify each file
    results: list[TriageResult] = []
    archive_count = 0

    for filename in pdfs:
        # Check if it's an older version first
        if filename in older_versions:
            result = TriageResult(
                filename=filename,
                category=FileCategory.OLDER_VERSION,
                action=TriageAction.ARCHIVE,
                reason="Oudere versie",
                newer_version=older_versions[filename],
            )
        else:
            result = classify_file(filename)

        if limit is not None and result.action == TriageAction.ARCHIVE:
            archive_count += 1
            if archive_count > limit:
                # Still classify but don't count beyond limit
                continue

        results.append(result)

    return results


def execute_triage(
    raw_dir: Path,
    results: list[TriageResult],
    dry_run: bool = True,
) -> tuple[int, int]:
    """Move archived files to raw/old/.

    Returns: (kept_count, archived_count)
    """
    old_dir = raw_dir / "old"
    kept = 0
    archived = 0

    for r in results:
        if r.action == TriageAction.KEEP:
            kept += 1
            continue

        src = raw_dir / r.filename
        if not src.exists():
            continue

        if dry_run:
            archived += 1
        else:
            old_dir.mkdir(exist_ok=True)
            dst = old_dir / r.filename
            shutil.move(str(src), str(dst))
            archived += 1

    return kept, archived
