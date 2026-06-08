"""Route a DocumentMap's sections/tables to each extraction bundle.

Deterministic, recall-first. Heading-primary anchor matching (body fallback only
when the heading matched nothing), plus a keyword-independent salary-grid rescue
that guarantees wage tables reach `remuneration`. Guarantees coverage (every
section reaches >=1 bundle) and falls back to the whole document for any bundle
whose slice is empty ('veiligheid boven besparing'), recording that visibly.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from cao_engine.extraction.sectioned.document_map import DocumentMap, MappedSection
from cao_engine.extraction.sectioned.sections import SECTIONS, SectionSpec

_MIN_SLICE_CHARS = 200      # below this a slice is "empty" -> whole-doc fallback
_HEAD_SECTIONS = 3          # identity always gets the first N sections (front matter)
_REMUNERATION_KEY = "remuneration"
_MONEY = re.compile(r"\b\d{1,3}[.,]\d{2}\b")  # two-decimal currency/wage number
_SALARY_GRID_MIN = 6        # >= this many money numbers in a table => a wage grid


@dataclass
class SectionRoutingInfo:
    matched_sections: int
    matched_tables: int
    char_size: int
    fallback_used: bool


@dataclass
class RoutingResult:
    inputs: dict[str, str]
    report: dict[str, SectionRoutingInfo]


def _heading_match(section: MappedSection, anchors: tuple[str, ...]) -> bool:
    h = (section.heading or "").lower()
    return any(a in h for a in anchors)


def _body_match(section: MappedSection, anchors: tuple[str, ...]) -> bool:
    b = section.body.lower()
    return any(a in b for a in anchors)


def _has_salary_grid(section: MappedSection) -> bool:
    if section.tables:
        return any(len(_MONEY.findall(t.content)) >= _SALARY_GRID_MIN for t in section.tables)
    # Defend against inline-only OCR (empty page.tables, wage data left in the markdown):
    # when a section has no extracted tables, scan its body for a wage grid. Scoped to the
    # no-tables case so the common path (tables populated, content also inlined in the body)
    # does not over-recall prose money amounts into remuneration.
    return len(_MONEY.findall(section.body)) >= _SALARY_GRID_MIN


def _assemble(secs: list[MappedSection]) -> str:
    return "\n\n".join(s.text for s in secs if s.text)


def route_sections(
    doc_map: DocumentMap,
    specs: list[SectionSpec] = SECTIONS,
    fallback_markdown: str | None = None,
) -> RoutingResult:
    fallback = fallback_markdown if fallback_markdown is not None else doc_map.full_markdown()
    matched: dict[str, list[MappedSection]] = {spec.key: [] for spec in specs}

    # 1. heading-primary; body only when the heading matched no bundle
    for section in doc_map.sections:
        heading_keys = [
            spec.key for spec in specs
            if spec.routing_anchors and _heading_match(section, spec.routing_anchors)
        ]
        if heading_keys:
            for key in heading_keys:
                matched[key].append(section)
        else:
            for spec in specs:
                if spec.routing_anchors and _body_match(section, spec.routing_anchors):
                    matched[spec.key].append(section)
        # salary-grid rescue (recall-first): a wage table always reaches remuneration
        if _REMUNERATION_KEY in matched and _has_salary_grid(section):
            matched[_REMUNERATION_KEY].append(section)

    # 2. coverage snapshot: sections already claimed by anchor/salary rules.
    # Taken BEFORE the identity head-extension so front-matter inclusion
    # does not rob the catch-all of genuinely unmatched (orphan) sections.
    assigned = {s.index for secs in matched.values() for s in secs}

    # 3. identity always gets the document head (preamble + first sections)
    ident = next((s for s in specs if s.key == "identity"), None)
    if ident is not None:
        matched[ident.key].extend(doc_map.sections[:_HEAD_SECTIONS])

    # 4. coverage: unmatched sections -> catch-all bundle
    catch_all = next((s for s in specs if s.is_catch_all), None)
    if catch_all is not None:
        matched[catch_all.key].extend(
            s for s in doc_map.sections if s.index not in assigned
        )

    # 5. de-dup per bundle (a section may be added twice: heading + rescue, or + head),
    #    assemble slices, empty-slice fallback (visible flag)
    inputs: dict[str, str] = {}
    report: dict[str, SectionRoutingInfo] = {}
    for spec in specs:
        seen: set[int] = set()
        secs: list[MappedSection] = []
        for s in sorted(matched[spec.key], key=lambda s: s.index):
            if s.index not in seen:
                seen.add(s.index)
                secs.append(s)
        slice_md = _assemble(secs)
        fallback_used = len(slice_md) < _MIN_SLICE_CHARS
        if fallback_used:
            slice_md = fallback
        inputs[spec.key] = slice_md
        report[spec.key] = SectionRoutingInfo(
            matched_sections=len(secs),
            matched_tables=sum(len(s.tables) for s in secs),
            char_size=len(slice_md),
            fallback_used=fallback_used,
        )
    return RoutingResult(inputs=inputs, report=report)
