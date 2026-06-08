# OCR-First Document Map & Section Routing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Insert a deterministic document-mapping + section-routing stage between OCR and the Fase E sectioned extractor, so each of the 6 passes receives only its relevant slice (sections + tables) instead of the whole document.

**Architecture:** Read the sibling `.ocr.json` (an `OCRResult`) → `build_document_map` produces an ordered `DocumentMap` (sections with their tables, parsed from headings + table placeholders) → `route_sections` keyword-anchors each Fase E bundle to its slice (coverage-guaranteed, empty-slice falls back to whole-doc with a visible flag) → `SectionedGeminiExtractor.extract(..., routed_inputs=...)`. Extraction logic, schemas, merge, and Fase C provenance are unchanged. Pure functions where possible; file-IO only in the CLI.

**Tech Stack:** Python 3.11+, dataclasses, Pydantic v2 (`OCRResult`), Typer CLI, pytest (`online` marker exists; this plan adds offline + one local-data integration test + one online smoke).

**Spec:** `docs/superpowers/specs/2026-06-07-ocr-first-document-map-design.md`

**Branch:** create `feat/cao-centraal-ocr-routing` from `master` (master already contains Fase E).

---

## File Structure

- **Create** `src/cao_engine/extraction/sectioned/document_map.py` — `MappedTable`, `MappedSection`, `DocumentMap` dataclasses + `build_document_map(OCRResult) -> DocumentMap`. Pure, deterministic.
- **Create** `src/cao_engine/extraction/sectioned/routing.py` — `SectionRoutingInfo`, `RoutingResult` dataclasses + `route_sections(DocumentMap, specs, fallback_markdown) -> RoutingResult`. Pure.
- **Modify** `src/cao_engine/extraction/sectioned/sections.py` — add `routing_anchors` + `is_catch_all` fields to `SectionSpec`; populate per bundle; neutralize the `build_prompt` "COMPLETE" wording.
- **Modify** `src/cao_engine/extraction/sectioned/gemini_sectioned.py` — `extract` accepts optional `routed_inputs`.
- **Modify** `src/cao_engine/extraction/sectioned/__init__.py` — export the new public names.
- **Modify** `src/cao_engine/cli.py` — load `.ocr.json`, build map+routing, pass `routed_inputs` to both the Gemini pass and the Mistral provenance pass; add `--no-routing` flag.
- **Test** `tests/sectioned/test_document_map.py`, `tests/sectioned/test_routing.py`, `tests/sectioned/test_gemini_sectioned.py` (extend), `tests/sectioned/test_document_map_integration.py`, `tests/sectioned/test_online_validation.py` (extend).

---

## Task 1: DocumentMap data model + build_document_map

**Files:**
- Create: `src/cao_engine/extraction/sectioned/document_map.py`
- Test: `tests/sectioned/test_document_map.py`
- Modify: `src/cao_engine/extraction/sectioned/__init__.py`

- [ ] **Step 1: Write the failing test**

Create `tests/sectioned/test_document_map.py`:

```python
"""Unit tests for build_document_map (pure, no network)."""
from cao_engine.extraction.sectioned.document_map import (
    DocumentMap,
    MappedSection,
    build_document_map,
)
from cao_engine.ocr.models import OCRPage, OCRResult, OCRTable, OCRUsageInfo


def _ocr(pages: list[OCRPage]) -> OCRResult:
    return OCRResult(
        model="test",
        pages=pages,
        usage_info=OCRUsageInfo(pages_processed=len(pages)),
        source_file="test.pdf",
    )


def test_headings_become_ordered_sections():
    ocr = _ocr([
        OCRPage(index=0, markdown="# Hoofdstuk 1 Loon\nIntro.\n## 1.1 Salaris\nSalaristekst."),
    ])
    doc = build_document_map(ocr)
    assert [s.heading for s in doc.sections] == ["Hoofdstuk 1 Loon", "1.1 Salaris"]
    assert [s.level for s in doc.sections] == [1, 2]


def test_table_placeholder_attaches_to_current_section_and_inlines():
    ocr = _ocr([
        OCRPage(
            index=0,
            markdown="## 1.1 Salaris\nZie [tbl-0.md](tbl-0.md) hierboven.",
            tables=[OCRTable(id="tbl-0.md", content="| A | B |\n| --- | --- |\n| 1 | 2 |")],
        ),
    ])
    doc = build_document_map(ocr)
    salaris = doc.sections[0]
    assert len(salaris.tables) == 1
    assert salaris.tables[0].id == "tbl-0.md"
    assert "| A | B |" in salaris.body  # table content inlined into body


def test_page_without_leading_heading_continues_previous_section():
    ocr = _ocr([
        OCRPage(index=0, markdown="## 1.1 Salaris\nDeel een."),
        OCRPage(index=1, markdown="Deel twee zonder kop.\n## 1.2 Verlof\nVerloftekst."),
    ])
    doc = build_document_map(ocr)
    assert [s.heading for s in doc.sections] == ["1.1 Salaris", "1.2 Verlof"]
    salaris = doc.sections[0]
    assert "Deel twee zonder kop." in salaris.body
    assert salaris.page_start == 0 and salaris.page_end == 1


def test_text_before_first_heading_becomes_preamble():
    ocr = _ocr([OCRPage(index=0, markdown="Voorblad tekst.\n# Hoofdstuk 1\nInhoud.")])
    doc = build_document_map(ocr)
    assert doc.sections[0].heading is None
    assert doc.sections[0].level == 0
    assert "Voorblad tekst." in doc.sections[0].body


def test_full_markdown_reproduces_content_and_all_tables():
    ocr = _ocr([
        OCRPage(
            index=0,
            markdown="## A\ntekst [tbl-0.md](tbl-0.md)",
            tables=[OCRTable(id="tbl-0.md", content="| x |")],
        ),
    ])
    doc = build_document_map(ocr)
    assert isinstance(doc, DocumentMap)
    assert len(doc.all_tables()) == 1
    full = doc.full_markdown()
    assert "## A" in full and "| x |" in full
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/sectioned/test_document_map.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cao_engine.extraction.sectioned.document_map'`

- [ ] **Step 3: Write minimal implementation**

Create `src/cao_engine/extraction/sectioned/document_map.py`:

```python
"""Build a structural map of an OCR'd CAO: ordered sections + their tables.

Deterministic and pure (no network, no LLM). Consumes an OCRResult and produces
a DocumentMap whose section bodies, concatenated, reproduce the document text.
Headers/footers and page markers are intentionally excluded as boilerplate.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from cao_engine.ocr.models import OCRResult

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass
class MappedTable:
    id: str
    content: str
    page_index: int


@dataclass
class MappedSection:
    index: int
    heading: str | None  # None = preamble / front-matter (text before the first heading)
    level: int           # 0 for preamble, else 1-6
    page_start: int
    page_end: int
    body: str = ""
    tables: list[MappedTable] = field(default_factory=list)

    @property
    def text(self) -> str:
        """Heading + body as markdown (used to assemble routed slices)."""
        head = f"{'#' * self.level} {self.heading}\n" if self.heading else ""
        return f"{head}{self.body}".strip()


@dataclass
class DocumentMap:
    sections: list[MappedSection]

    def all_tables(self) -> list[MappedTable]:
        return [t for s in self.sections for t in s.tables]

    def full_markdown(self) -> str:
        return "\n\n".join(s.text for s in self.sections if s.text)


def build_document_map(ocr_result: OCRResult) -> DocumentMap:
    sections: list[MappedSection] = []
    current: MappedSection | None = None

    def _open(heading: str | None, level: int, page_index: int) -> MappedSection:
        section = MappedSection(
            index=len(sections), heading=heading, level=level,
            page_start=page_index, page_end=page_index,
        )
        sections.append(section)
        return section

    for page in ocr_result.pages:
        tables_by_id = {t.id: t for t in page.tables}
        seen_ids: set[str] = set()
        for raw_line in page.markdown.splitlines():
            match = _HEADING_RE.match(raw_line.strip())
            if match:
                current = _open(match.group(2).strip(), len(match.group(1)), page.index)
                continue
            if current is None:
                current = _open(None, 0, page.index)  # preamble
            current.page_end = page.index
            line = raw_line
            for tid, table in tables_by_id.items():
                placeholder = f"[{tid}]({tid})"
                if placeholder in line:
                    line = line.replace(placeholder, f"\n{table.content}\n")
                    current.tables.append(
                        MappedTable(id=tid, content=table.content, page_index=page.index)
                    )
                    seen_ids.add(tid)
            current.body += line + "\n"
        # defensive: tables whose placeholder never appeared in the markdown
        for tid, table in tables_by_id.items():
            if tid in seen_ids:
                continue
            if current is None:
                current = _open(None, 0, page.index)
            current.page_end = page.index
            current.body += f"\n{table.content}\n"
            current.tables.append(
                MappedTable(id=tid, content=table.content, page_index=page.index)
            )

    return DocumentMap(sections=sections)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/sectioned/test_document_map.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Export from the package**

Modify `src/cao_engine/extraction/sectioned/__init__.py` — add the imports and `__all__` entries:

```python
from cao_engine.extraction.sectioned.document_map import (
    DocumentMap,
    MappedSection,
    MappedTable,
    build_document_map,
)
from cao_engine.extraction.sectioned.gemini_sectioned import (
    SectionedGeminiExtractor,
    make_gemini_generate,
)
from cao_engine.extraction.sectioned.merge import merge_sections
from cao_engine.extraction.sectioned.sections import SECTIONS, SectionSpec

__all__ = [
    "SectionedGeminiExtractor",
    "make_gemini_generate",
    "merge_sections",
    "SECTIONS",
    "SectionSpec",
    "DocumentMap",
    "MappedSection",
    "MappedTable",
    "build_document_map",
]
```

- [ ] **Step 6: Run ruff + the test module**

Run: `ruff check src/cao_engine/extraction/sectioned/document_map.py tests/sectioned/test_document_map.py && pytest tests/sectioned/test_document_map.py -q`
Expected: ruff clean, tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/cao_engine/extraction/sectioned/document_map.py tests/sectioned/test_document_map.py src/cao_engine/extraction/sectioned/__init__.py
git commit -m "feat: add DocumentMap + build_document_map (OCR structure mapping)"
```

---

## Task 2: SectionSpec routing fields + anchors

**Files:**
- Modify: `src/cao_engine/extraction/sectioned/sections.py`
- Test: `tests/sectioned/test_sections.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/sectioned/test_sections.py`:

```python
def test_every_section_has_routing_anchors_or_is_catch_all():
    from cao_engine.extraction.sectioned.sections import SECTIONS
    for spec in SECTIONS:
        assert spec.routing_anchors or spec.is_catch_all, spec.key


def test_exactly_one_catch_all_section():
    from cao_engine.extraction.sectioned.sections import SECTIONS
    catch_alls = [s.key for s in SECTIONS if s.is_catch_all]
    assert catch_alls == ["supplementary"], catch_alls


def test_remuneration_anchors_include_salary_terms():
    from cao_engine.extraction.sectioned.sections import SECTIONS
    rem = next(s for s in SECTIONS if s.key == "remuneration")
    assert "salaris" in rem.routing_anchors and "loon" in rem.routing_anchors
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/sectioned/test_sections.py -k routing -v`
Expected: FAIL with `AttributeError: 'SectionSpec' object has no attribute 'routing_anchors'`

- [ ] **Step 3: Add the fields to SectionSpec**

In `src/cao_engine/extraction/sectioned/sections.py`, extend the dataclass (keep existing fields/`__post_init__`):

```python
@dataclass(frozen=True)
class SectionSpec:
    key: str
    top_level_keys: list[str]
    prompt_focus: str
    max_depth: int = 8  # per-section nesting cap; deep bundles need a lower value (live-API limit)
    routing_anchors: tuple[str, ...] = ()  # keyword anchors for OCR-map section routing
    is_catch_all: bool = False  # unmatched sections are routed here (coverage guarantee)
    schema: dict = field(default=None)
```

- [ ] **Step 4: Populate anchors on each SECTIONS entry**

Add the keyword arguments to the existing `SectionSpec(...)` entries in `SECTIONS` (do not change `top_level_keys`/`prompt_focus`/`max_depth`):

```python
# identity (broad term 'cao' removed — it matched ~85 sections):
        routing_anchors=("looptijd", "werkingssfeer", "begrippen", "definities", "partijen"),
# remuneration:
        routing_anchors=("salaris", "loon", "loontabel", "loonsverhoging", "functiegroep",
                         "salarisschaal", "salarisgroep", "periodiek", "garantieloon", "uurloon"),
# allowances (broad term 'vergoeding' removed):
        routing_anchors=("toeslag", "ort", "onregelmatig", "ploegen", "overwerk",
                         "reiskosten", "vakantietoeslag", "vakantiegeld", "reisuren"),
# leave:
        routing_anchors=("verlof", "vakantie", "adv", "atv", "feestdag", "ziekte",
                         "arbeidsongeschikt", "roostervrije"),
# pension:
        routing_anchors=("pensioen", "ikb", "keuzebudget", "generatiepact",
                         "duurzame inzetbaarheid"),
# supplementary (broad term 'regeling' removed — it stole salary 'Basisregeling' sections):
        routing_anchors=("eenmalig", "uitkering", "bonus", "afbouw", "jubileum"),
        is_catch_all=True,
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/sectioned/test_sections.py -v`
Expected: PASS (existing + 3 new tests pass).

- [ ] **Step 6: Commit**

```bash
git add src/cao_engine/extraction/sectioned/sections.py tests/sectioned/test_sections.py
git commit -m "feat: add routing_anchors + catch-all to SectionSpec"
```

---

## Task 3: route_sections

**Files:**
- Create: `src/cao_engine/extraction/sectioned/routing.py`
- Test: `tests/sectioned/test_routing.py`
- Modify: `src/cao_engine/extraction/sectioned/__init__.py`

- [ ] **Step 1: Write the failing test**

Create `tests/sectioned/test_routing.py`:

```python
"""Unit tests for route_sections (pure, no network)."""
from cao_engine.extraction.sectioned.document_map import DocumentMap, MappedSection, MappedTable
from cao_engine.extraction.sectioned.routing import route_sections
from cao_engine.extraction.sectioned.sections import SECTIONS

_LONG = "x " * 300  # > _MIN_SLICE_CHARS so a matched slice is not treated as empty


def _section(index, heading, body="", tables=None):
    return MappedSection(
        index=index, heading=heading, level=2, page_start=0, page_end=0,
        body=body, tables=tables or [],
    )


def test_salary_section_routes_to_remuneration_by_heading():
    doc = DocumentMap(sections=[
        _section(0, "Salaris en loon", body=_LONG,
                 tables=[MappedTable(id="t0", content="| trede |", page_index=0)]),
    ])
    result = route_sections(doc, SECTIONS, fallback_markdown="FALLBACK")
    assert "Salaris en loon" in result.inputs["remuneration"]
    assert result.report["remuneration"].fallback_used is False
    assert result.report["remuneration"].matched_tables == 1


def test_wage_grid_table_rescues_section_into_remuneration():
    # heading matches NO bundle, body has no anchors, but the table is a wage grid
    # (>= 6 two-decimal money numbers) -> recall-first rescue routes it to remuneration.
    wage = "\n".join(f"| groep {i} | {10 + i},{i:02d} |" for i in range(8))
    doc = DocumentMap(sections=[
        _section(0, "Bijlage 1 Basisregeling", body=_LONG + "\n" + wage,
                 tables=[MappedTable(id="t0", content=wage, page_index=0)]),
    ])
    result = route_sections(doc, SECTIONS, fallback_markdown="FALLBACK")
    assert "Bijlage 1 Basisregeling" in result.inputs["remuneration"]
    assert result.report["remuneration"].fallback_used is False


def test_unmatched_section_goes_to_catch_all_supplementary():
    doc = DocumentMap(sections=[_section(0, "Iets heel exotisch", body=_LONG)])
    result = route_sections(doc, SECTIONS, fallback_markdown="FALLBACK")
    assert "Iets heel exotisch" in result.inputs["supplementary"]


def test_empty_slice_falls_back_to_whole_doc_with_flag():
    # only a salary section exists -> leave/pension etc. match nothing -> fallback
    doc = DocumentMap(sections=[_section(0, "Salaris", body=_LONG)])
    result = route_sections(doc, SECTIONS, fallback_markdown="WHOLE_DOC_FALLBACK")
    assert result.inputs["leave"] == "WHOLE_DOC_FALLBACK"
    assert result.report["leave"].fallback_used is True


def test_coverage_no_section_is_dropped():
    doc = DocumentMap(sections=[
        _section(0, "Salaris", body=_LONG),
        _section(1, "Verlof en vakantie", body=_LONG),
        _section(2, "Onbekend kopje", body=_LONG),
    ])
    result = route_sections(doc, SECTIONS, fallback_markdown="FALLBACK")
    everything = "\n".join(result.inputs.values())
    assert "Salaris" in everything
    assert "Verlof en vakantie" in everything
    assert "Onbekend kopje" in everything  # landed in catch-all


def test_identity_always_includes_document_head():
    doc = DocumentMap(sections=[
        _section(0, "Voorblad partijen", body=_LONG),
        _section(1, "Salaris", body=_LONG),
    ])
    result = route_sections(doc, SECTIONS, fallback_markdown="FALLBACK")
    assert "Voorblad partijen" in result.inputs["identity"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/sectioned/test_routing.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cao_engine.extraction.sectioned.routing'`

- [ ] **Step 3: Write minimal implementation**

Create `src/cao_engine/extraction/sectioned/routing.py`:

```python
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
    return any(len(_MONEY.findall(t.content)) >= _SALARY_GRID_MIN for t in section.tables)


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

    # 2. identity always gets the document head (preamble + first sections)
    ident = next((s for s in specs if s.key == "identity"), None)
    if ident is not None:
        matched[ident.key].extend(doc_map.sections[:_HEAD_SECTIONS])

    # 3. coverage: unmatched sections -> catch-all bundle
    assigned = {s.index for secs in matched.values() for s in secs}
    catch_all = next((s for s in specs if s.is_catch_all), None)
    if catch_all is not None:
        matched[catch_all.key].extend(
            s for s in doc_map.sections if s.index not in assigned
        )

    # 4. de-dup per bundle (a section may be added twice: heading + rescue, or + head),
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/sectioned/test_routing.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Export from the package**

In `src/cao_engine/extraction/sectioned/__init__.py`, add:

```python
from cao_engine.extraction.sectioned.routing import (
    RoutingResult,
    SectionRoutingInfo,
    route_sections,
)
```

and add `"RoutingResult"`, `"SectionRoutingInfo"`, `"route_sections"` to `__all__`.

- [ ] **Step 6: Run ruff + tests**

Run: `ruff check src/cao_engine/extraction/sectioned/routing.py tests/sectioned/test_routing.py && pytest tests/sectioned/test_routing.py -q`
Expected: ruff clean, tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/cao_engine/extraction/sectioned/routing.py tests/sectioned/test_routing.py src/cao_engine/extraction/sectioned/__init__.py
git commit -m "feat: add route_sections (anchor routing + coverage + fallback)"
```

---

## Task 4: SectionedGeminiExtractor accepts routed_inputs

**Files:**
- Modify: `src/cao_engine/extraction/sectioned/gemini_sectioned.py`
- Modify: `src/cao_engine/extraction/sectioned/sections.py` (build_prompt wording)
- Test: `tests/sectioned/test_gemini_sectioned.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/sectioned/test_gemini_sectioned.py`:

```python
def test_routed_inputs_feed_each_pass_its_own_slice():
    from cao_engine.extraction.sectioned import SectionedGeminiExtractor
    from cao_engine.extraction.sectioned.sections import SECTIONS

    seen: dict[str, str] = {}

    # capture which markdown each section pass received (prompt embeds the markdown)
    specs = SECTIONS

    def fake_generate(prompt: str, schema: dict) -> tuple[str, str]:
        for spec in specs:
            if spec.prompt_focus[:20] in prompt:
                seen[spec.key] = prompt
        return "{}", "STOP"

    routed = {spec.key: f"SLICE_FOR_{spec.key}" for spec in specs}
    SectionedGeminiExtractor(fake_generate).extract("WHOLE_DOC", "X", routed_inputs=routed)

    assert "SLICE_FOR_remuneration" in seen["remuneration"]
    assert "WHOLE_DOC" not in seen["remuneration"]


def test_without_routed_inputs_uses_whole_markdown():
    from cao_engine.extraction.sectioned import SectionedGeminiExtractor

    prompts: list[str] = []

    def fake_generate(prompt: str, schema: dict) -> tuple[str, str]:
        prompts.append(prompt)
        return "{}", "STOP"

    SectionedGeminiExtractor(fake_generate).extract("WHOLE_DOC", "X")
    assert all("WHOLE_DOC" in p for p in prompts)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/sectioned/test_gemini_sectioned.py -k routed -v`
Expected: FAIL with `TypeError: extract() got an unexpected keyword argument 'routed_inputs'`

- [ ] **Step 3: Add the parameter**

In `src/cao_engine/extraction/sectioned/gemini_sectioned.py`, change the `extract` signature and the per-section markdown selection:

```python
    def extract(
        self,
        markdown: str,
        cao_name: str | None = None,
        routed_inputs: dict[str, str] | None = None,
    ) -> dict:
        slices: list[dict] = []
        meta: dict = {}
        for spec in self._sections:
            section_md = (
                routed_inputs[spec.key]
                if routed_inputs and spec.key in routed_inputs
                else markdown
            )
            finish: str | None = None
            try:
                text, finish = self._generate(spec.build_prompt(section_md, cao_name), spec.schema)
                data = json.loads(text)
                slices.append(data)
                meta[spec.key] = {"ok": True, "finish": finish}
                logger.info("section extracted", section=spec.key, finish=finish)
            except Exception as exc:  # API error, JSON parse (truncation), etc. -> isolate
                meta[spec.key] = {"ok": False, "finish": finish, "error": str(exc)}
                logger.warning("section failed", section=spec.key, finish=finish, error=str(exc))
        merged = merge_sections(slices)
        merged["_extraction_metadata"] = {
            "extractor": "gemini-sectioned",
            "cao_name": cao_name,
            "routed": routed_inputs is not None,
            "sections_ok": [k for k, m in meta.items() if m["ok"]],
            "sections_failed": [k for k, m in meta.items() if not m["ok"]],
        }
        merged["_section_meta"] = meta
        return merged
```

- [ ] **Step 4: Neutralize the build_prompt "COMPLETE" wording**

In `src/cao_engine/extraction/sectioned/sections.py`, change the final line of `build_prompt` so a focused slice is not labelled the whole CAO:

```python
    def build_prompt(self, markdown: str, cao_name: str | None) -> str:
        return (
            f"{_BASE}\nFOCUS: {self.prompt_focus}\n\n"
            f"CAO Name: {cao_name or 'Unknown'}\n\n"
            f"CAO Document (Markdown from Mistral OCR):\n\n{markdown}"
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/sectioned/test_gemini_sectioned.py -v`
Expected: PASS (existing + 2 new tests).

- [ ] **Step 6: Commit**

```bash
git add src/cao_engine/extraction/sectioned/gemini_sectioned.py src/cao_engine/extraction/sectioned/sections.py tests/sectioned/test_gemini_sectioned.py
git commit -m "feat: SectionedGeminiExtractor.extract accepts routed_inputs"
```

---

## Task 5: CLI wiring (load .ocr.json, route, pass routed_inputs) + --no-routing

**Files:**
- Modify: `src/cao_engine/cli.py` (`extract_setu_pipeline`, ~716-850)

- [ ] **Step 1: Add the --no-routing option to the signature**

In `extract_setu_pipeline`, add after the `provenance` option (keep the others):

```python
    no_routing: bool = typer.Option(
        False,
        "--no-routing",
        help="Disable OCR-map section routing (feed the whole document to every pass)",
    ),
```

- [ ] **Step 2: Build routed_inputs after reading markdown_text**

Insert directly after `markdown_text = ocr_path.read_text(encoding="utf-8")` (line ~748) and before the Step 1 console prints:

```python
    # OCR-first routing: build a document map from the sibling .ocr.json and route
    # each sectioned pass to its relevant slice. Falls back to whole-doc on any issue.
    routed_inputs = None
    if sectioned and not no_routing:
        try:
            from cao_engine.extraction.sectioned.document_map import build_document_map
            from cao_engine.extraction.sectioned.routing import route_sections
            from cao_engine.extraction.sectioned.sections import SECTIONS
            from cao_engine.ocr.models import OCRResult

            ocr_json = ocr_path.parent / (ocr_path.stem + ".ocr.json")
            if ocr_json.exists():
                ocr_result = OCRResult.model_validate_json(ocr_json.read_text(encoding="utf-8"))
                result = route_sections(build_document_map(ocr_result), SECTIONS, markdown_text)
                routed_inputs = result.inputs
                summary = ", ".join(
                    f"{k}:{r.char_size // 1000}k{'(FB)' if r.fallback_used else ''}"
                    for k, r in result.report.items()
                )
                console.print(f"[dim]  Routing: {summary}[/dim]")
            else:
                console.print("[yellow]  No .ocr.json sibling; routing disabled (whole-doc)[/yellow]")
        except Exception as exc:  # routing is advisory; never fail the command
            console.print(f"[yellow]  Routing skipped ({exc}); whole-doc[/yellow]")
            routed_inputs = None
```

- [ ] **Step 3: Pass routed_inputs to the Gemini pass**

Change line ~765 from:

```python
        gemini_output = SectionedGeminiExtractor(generate).extract(markdown_text, cao)
```

to:

```python
        gemini_output = SectionedGeminiExtractor(generate).extract(
            markdown_text, cao, routed_inputs=routed_inputs
        )
```

- [ ] **Step 4: Pass routed_inputs to the Mistral provenance pass**

Change line ~840 from:

```python
                mistral_doc = SectionedGeminiExtractor(m_generate).extract(markdown_text, cao)
```

to:

```python
                mistral_doc = SectionedGeminiExtractor(m_generate).extract(
                    markdown_text, cao, routed_inputs=routed_inputs
                )
```

- [ ] **Step 5: Verify the CLI imports cleanly and ruff passes**

Run: `python -c "from cao_engine.cli import app" && ruff check src/cao_engine/cli.py`
Expected: no import error, ruff clean.

- [ ] **Step 6: Verify the full suite still passes (no regressions)**

Run: `pytest -q -m "not online"`
Expected: no NEW failures vs the pre-existing baseline (the repo has known pre-existing failures; compare counts — new code must add 0 failures).

- [ ] **Step 7: Commit**

```bash
git add src/cao_engine/cli.py
git commit -m "feat: wire OCR-map routing into extract-setu-pipeline (--no-routing escape hatch)"
```

---

## Task 6: Integration test on the real Bouw .ocr.json

**Files:**
- Test: `tests/sectioned/test_document_map_integration.py`

- [ ] **Step 1: Write the test (skips if the local data file is absent)**

Create `tests/sectioned/test_document_map_integration.py`:

```python
"""Integration: build a map + route on the real Bouw & Infra OCR output (179 pages).

Skipped automatically when the local data file is absent (e.g. CI without data/).
No network: pure functions over an on-disk .ocr.json.
"""
from pathlib import Path

import pytest

from cao_engine.extraction.sectioned.document_map import build_document_map
from cao_engine.extraction.sectioned.routing import route_sections
from cao_engine.extraction.sectioned.sections import SECTIONS
from cao_engine.ocr.models import OCRResult

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OCR_JSON = _REPO_ROOT / "data" / "ocr" / (
    "488-bouw-en-infra-cao-01-01-2025-tm-31-03-2027-v24042026.ocr.json"
)

pytestmark = pytest.mark.skipif(not OCR_JSON.exists(), reason="Bouw .ocr.json not on disk")


def _doc_and_routing():
    ocr = OCRResult.model_validate_json(OCR_JSON.read_text(encoding="utf-8"))
    doc = build_document_map(ocr)
    full = ocr.full_markdown()
    return doc, route_sections(doc, SECTIONS, full), full


def test_map_captures_all_71_tables_and_many_sections():
    doc, _, _ = _doc_and_routing()
    assert len(doc.all_tables()) == 71  # matches the verified OCR table count
    assert len(doc.sections) > 20       # a 179-page CAO has many headed sections


def test_remuneration_slice_contains_functiegroep_wage_scale():
    """Independent ground truth: functiegroep A wages (tbl-14), hand-verified from the OCR."""
    _, routing, _ = _doc_and_routing()
    rem = routing.inputs["remuneration"]
    assert "functiegroep" in rem.lower()
    assert "17,43" in rem   # functiegroep A, 1/1/2025
    assert "19,23" in rem   # functiegroep A, 1/1/2027


def test_every_wage_grid_table_lands_in_remuneration():
    """The core promise: no salary table is misrouted away from remuneration."""
    import re
    doc, routing, _ = _doc_and_routing()
    money = re.compile(r"\b\d{1,3}[.,]\d{2}\b")
    rem = routing.inputs["remuneration"]
    wage_sections = [
        s for s in doc.sections
        if any(len(money.findall(t.content)) >= 6 for t in s.tables)
    ]
    assert wage_sections, "expected wage-grid sections in the Bouw CAO"
    missing = [s.heading for s in wage_sections if s.text not in rem]
    assert missing == [], f"wage sections missing from remuneration: {missing[:5]}"


def test_remuneration_slice_is_smaller_than_full_doc():
    _, routing, full = _doc_and_routing()
    assert routing.report["remuneration"].char_size < len(full) * 0.7


def test_leave_slice_contains_verlof():
    _, routing, _ = _doc_and_routing()
    assert "verlof" in routing.inputs["leave"].lower()


def test_no_bundle_falls_back_on_this_real_doc():
    _, routing, _ = _doc_and_routing()
    fell_back = [k for k, r in routing.report.items() if r.fallback_used]
    assert fell_back == [], fell_back
```

- [ ] **Step 2: Run the integration test**

Run: `pytest tests/sectioned/test_document_map_integration.py -v`
Expected: PASS if the Bouw `.ocr.json` is present; SKIPPED otherwise. The prototype run already confirmed the numbers (71 tables, 35/35 wage-grid tables in remuneration, functiegroep wages present, no fallback). If the size threshold needs nudging, record the observed numbers in the commit — never weaken the wage-grid / no-fallback assertions.

- [ ] **Step 3: Commit**

```bash
git add tests/sectioned/test_document_map_integration.py
git commit -m "test: integration map+routing on real Bouw OCR (size reduction + coverage)"
```

---

## Task 7: Online anchor smoke with routing

**Files:**
- Test: `tests/sectioned/test_online_validation.py` (extend)

- [ ] **Step 1: Add a routed online smoke test**

Append to `tests/sectioned/test_online_validation.py` (it already imports `SectionedGeminiExtractor`, `make_gemini_generate`, `json`, `os`, `pytest`, and defines `OCR`). Add the needed imports at the top of the file (next to the existing imports):

```python
from cao_engine.extraction.sectioned.document_map import build_document_map
from cao_engine.extraction.sectioned.routing import route_sections
from cao_engine.extraction.sectioned.sections import SECTIONS
from cao_engine.ocr.models import OCRResult
```

Then add:

```python
@pytest.mark.skipif(not os.environ.get("GOOGLE_API_KEY"), reason="no GOOGLE_API_KEY")
def test_ikea_sectioned_with_routing_still_hits_salary_anchors():
    """Routing must not route the salary data away: >=20 salary steps with routing on."""
    ocr_json = OCR.parent / (OCR.stem + ".ocr.json")
    if not ocr_json.exists():
        pytest.skip("ikea .ocr.json not on disk")

    markdown = OCR.read_text(encoding="utf-8")
    ocr_result = OCRResult.model_validate_json(ocr_json.read_text(encoding="utf-8"))
    routed = route_sections(build_document_map(ocr_result), SECTIONS, markdown).inputs

    generate = make_gemini_generate(os.environ["GOOGLE_API_KEY"], "gemini-3.5-flash", "LOW")
    doc = SectionedGeminiExtractor(generate).extract(
        markdown, "IKEA CAO 2023-2024", routed_inputs=routed
    )

    assert all(m["ok"] for m in doc["_section_meta"].values()), doc["_section_meta"]
    steps = json.dumps(doc.get("remuneration", []), ensure_ascii=False).count('"value"')
    assert steps >= 20, f"only {steps} salary steps with routing"
```

- [ ] **Step 2: Run offline suite to confirm collection is clean**

Run: `pytest tests/sectioned/ -q -m "not online"`
Expected: all non-online sectioned tests pass; the new online test is deselected.

- [ ] **Step 3: (Manual / when API key available) Run the online gate**

Run: `pytest tests/sectioned/test_online_validation.py -m online -v`
Expected: PASS — both the original whole-doc anchor test and the new routed test hit ground truth (proves routing preserves the salary data end-to-end).

- [ ] **Step 4: Commit**

```bash
git add tests/sectioned/test_online_validation.py
git commit -m "test: online smoke that routing preserves salary anchors (ikea)"
```

---

## Self-Review

**Spec coverage:** §3 dataflow → Tasks 1,3,4,5. §4 components → Task 1 (document_map), Task 3 (routing), Task 2 (SectionSpec fields), Task 4 (extractor), Task 5 (CLI). §5 mapping algorithm → Task 1. §6 routing rules (heading-primary + body-fallback + salary-grid rescue + tightened anchors, recall-first) → Tasks 2,3, validated by Task 6. §7 safety (coverage, empty-slice fallback+flag, mapping-fail, legacy .md) → Task 3 (coverage/fallback), Task 5 (mapping-fail try/except, missing .ocr.json). §8 provenance same routed input → Task 5 Step 4. §9 testing → Tasks 1,3,4,6,7. §10 untouched → respected (no edits to schemas/merge/provenance compute). All resolved decisions honored.

**Placeholder scan:** no TBD/TODO; every code step shows complete code; the one tunable (integration size threshold) has explicit guidance not to weaken the wage-grid / no-fallback safety assertions.

**Empirical pre-validation:** the mapping + routing logic was prototyped against the real Bouw `.ocr.json` before this plan was finalised — 71 tables mapped, **35/35 wage-grid tables route to remuneration**, functiegroep wages present in the remuneration slice, no bundle falls back. Task 6 encodes exactly these checks.

**Type consistency:** `build_document_map(OCRResult) -> DocumentMap`; `MappedSection.text`, `.tables`, `.body`, `.index` used consistently; `route_sections(doc_map, specs=SECTIONS, fallback_markdown=None) -> RoutingResult` with `.inputs`/`.report`; routing helpers `_heading_match`/`_body_match`/`_has_salary_grid` operate on `MappedSection`; `SectionRoutingInfo` fields (`matched_sections`, `matched_tables`, `char_size`, `fallback_used`) used identically in routing.py and tests; `extract(markdown, cao_name=None, routed_inputs=None)` consistent across Task 4 and Task 5 call sites; `is_catch_all`/`routing_anchors` defined in Task 2 and consumed in Task 3.

---

## Execution Handoff

Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, two-stage review (spec compliance, then code quality) between tasks.
2. **Inline Execution** — execute tasks in this session with checkpoints.

Before Task 1: create the branch `feat/cao-centraal-ocr-routing` from `master` (or an isolated worktree).
