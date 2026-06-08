# OCR-First Document Map & Section Routing — Design Spec

> **Date:** 2026-06-07 · **Status:** design spec (approved direction, ready for plan) · **Builds on:** Fase E (`extraction/sectioned/`)

## 1. Motivation

Today the sectioned extractor (Fase E) feeds **the entire OCR markdown** to **every** one of the 6 section passes. For a large CAO (Bouw & Infra: 406 KB / 179 pages) this means each pass re-parses the whole document, re-deriving structure 6× over. There is no map of *what lives where* and no targeting of *which content goes to which pass*.

The redirect (Rik): **start with Mistral OCR to map and annotate all structure first, then let a "normal" LLM do its work** on that pre-structured input. Approach A was chosen: OCR produces the structure/annotation; the LLM maps that to SETU.

### Empirical findings that shape this design (verified, not assumed)

- **`document_annotation` = max 8 pages** (Mistral recommends splitting); `bbox_annotation` has no page limit but operates per bounding-box (figures), not whole-document structure. ⇒ Mistral's *native* whole-document annotation is out for 179-page CAOs and would re-hit the SETU schema-complexity wall. We build the map ourselves.
- The OCR client (`ocr/client.py`) passes `table_format`/`extract_header`/`extract_footer` but **no annotation_format** → `response.document_annotation` is always `None`. The annotation capability is 0% used.
- **`page.tables` is richly populated** — Bouw `.ocr.json` has **71 tables across 53 pages**. Each `OCRTable` has `id`, `content` (markdown), `format`.
- **`OCRResult.full_markdown` (`ocr/models.py:43-61`) re-inlines tables**: page markdown contains a placeholder `[tbl-X.md](tbl-X.md)`; `full_markdown` replaces it with the table content. So the saved `.md` already contains every table (71× `| ---`). **There is no data loss today** — the tables already reach the LLM. The problem is purely the undifferentiated blob, not missing tables.

So the win is **not** "rescue lost tables." The win is: build an explicit structure map from the OCR output and feed each section pass only its relevant slice — cheaper, faster, less 65K-output truncation pressure, and the model works from structure instead of reverse-engineering it.

## 2. Goal & non-goals

**Goal:** Insert a deterministic mapping + routing stage between OCR and the sectioned extractor so each of the 6 passes receives a focused, relevant slice (sections + tables) instead of the full document. Extraction logic itself is unchanged.

**In scope:** a `DocumentMap` built from the `OCRResult`; keyword-anchored per-section routing; safety fallbacks; CLI wiring; tests including an integration test on the real Bouw `.ocr.json`.

**Non-goals (explicitly deferred):**
- Semantic LLM annotation of sections/tables (was "Approach 2") — optional later enhancement, separately costed.
- Native Mistral `document_annotation`/`bbox_annotation` (was "Approach 3") — rejected (8-page cap + schema wall).
- Any change to the Fase E section schemas, `merge_sections`, Fase C provenance computation, or the reviewer/judge-skip in sectioned mode.

## 3. Architecture & dataflow

```
PDF → Mistral OCR → OCRResult  (page.markdown + page.tables + headings + page index)   ← .ocr.json on disk
                       │
            build_document_map(ocr_result)
                       ▼
              DocumentMap   (ordered MappedSections, each carrying its MappedTables;
                             each annotated with heading, page range)
                       │
            route_sections(doc_map, SECTIONS)
                       ▼
        RoutingResult{ inputs: {section_key → focused markdown slice},
                       report: {section_key → SectionRoutingInfo} }
                       │
   SectionedGeminiExtractor.extract(markdown, cao, routed_inputs=inputs)   ← extraction UNCHANGED
                       ▼
            merge_sections() → canonical SETU → (Fase C provenance) → save
```

**Source = the sibling `.ocr.json` (an `OCRResult`), not the flat `.md`.** Only the `.ocr.json` carries `page.tables` as addressable objects and the per-page markdown with table placeholders, which lets us locate each table's exact section precisely.

## 4. Components & files

**New — `src/cao_engine/extraction/sectioned/document_map.py`**
- `MappedTable` (dataclass): `id: str`, `content: str`, `page_index: int`.
- `MappedSection` (dataclass): `index: int`, `heading: str | None` (None = preamble/front-matter), `level: int`, `page_start: int`, `page_end: int`, `body: str`, `tables: list[MappedTable]`.
- `DocumentMap` (dataclass): `sections: list[MappedSection]`, plus helpers `all_tables()` and `full_markdown()` (concatenation of every section — equals the whole doc, used by fallbacks).
- `build_document_map(ocr_result: OCRResult) -> DocumentMap` — deterministic, pure.

**New — `src/cao_engine/extraction/sectioned/routing.py`**
- `SectionRoutingInfo` (dataclass): `matched_sections: int`, `matched_tables: int`, `char_size: int`, `fallback_used: bool`.
- `RoutingResult` (dataclass): `inputs: dict[str, str]`, `report: dict[str, SectionRoutingInfo]`.
- `route_sections(doc_map: DocumentMap, specs: list[SectionSpec]) -> RoutingResult`.

**Modify — `sections.py`**
- Add `routing_anchors: tuple[str, ...] = ()` to `SectionSpec` (routing knowledge lives with the section definition). Populate per section (see §6).
- Add `is_catch_all: bool = False`; set `True` on `supplementary` so unmatched content lands there.

**Modify — `gemini_sectioned.py`**
- `extract(self, markdown, cao_name=None, routed_inputs: dict[str, str] | None = None)`. For each spec: `section_md = routed_inputs[spec.key] if routed_inputs and spec.key in routed_inputs else markdown`. Backward compatible (no `routed_inputs` → current behavior, identical output).

**Modify — `cli.py` (`extract_setu_pipeline`, sectioned branch ~755-840)**
- After reading `markdown_text`, attempt to load the sibling `.ocr.json`: `ocr_json = ocr_path.parent / (ocr_path.stem + ".ocr.json")`.
- If present and routing not disabled: `ocr_result = OCRResult.model_validate_json(ocr_json.read_text())` → `doc_map = build_document_map(ocr_result)` → `routing = route_sections(doc_map, SECTIONS)` → pass `routed_inputs=routing.inputs` to **both** the Gemini extract (line ~765) **and** the Mistral provenance extract (line ~840). Log `routing.report`.
- New flag `--no-routing` (default off → routing on) as an A/B escape hatch.
- If `.ocr.json` is missing → log a warning and fall back to whole-doc (`routed_inputs=None`).

**Modify — `SectionSpec.build_prompt`** — generalize the header line from "COMPLETE CAO Document" to "CAO Document (relevant excerpts, Markdown from Mistral OCR)" so a focused slice does not mislead the model into treating its slice as the entire CAO. (Wording-only; no schema change.)

## 5. `build_document_map` algorithm (deterministic)

Walk pages in `ocr_result.pages` order, maintaining a "current section":

1. **Headings:** within `page.markdown`, lines matching `^#{1,6}\s+(.*)` start a new `MappedSection` (heading text, level = number of `#`, `page_start = page.index`). Body accumulates the text between this heading and the next.
2. **Cross-page continuation:** a page that does not begin with a heading continues the current section (sections span page boundaries); update its `page_end`. Text before the first-ever heading → a synthetic preamble section (`heading=None`, `level=0`).
3. **Tables:** for each `table` in `page.tables`, locate `[{table.id}]({table.id})` in `page.markdown`. The table belongs to the section open at that placeholder's position. If the placeholder is absent (defensive), attach to the last section open on that page. Store as a `MappedTable` in that section's `tables` and inline its `content` into the section body at the placeholder position (so a routed slice reads as coherent markdown, mirroring `full_markdown`).

Pure and deterministic — no network, no LLM. Equivalent-content invariant: concatenating all sections' bodies reproduces the document text (minus the `<!-- Page -->` markers), so `DocumentMap.full_markdown()` is a safe fallback source.

## 6. Routing rules & anchors

**Principle: recall-first.** Because the 6 bundles own disjoint SETU keys, a section reaching *more* than one bundle is harmless (a pension pass simply finds no pension data in a salary section). The only fatal error is a salary table *not* reaching `remuneration` — then its scale/steps land in a bundle whose schema cannot hold them and vanish at merge. So routing maximises recall, especially for `remuneration`; smaller slices are a secondary benefit.

Matching, per `MappedSection`, in this order:
1. **Heading-primary:** if the section's **heading** contains any anchor (case-insensitive substring) of one or more specs, assign it to those specs. (Headings are the high-precision signal.)
2. **Body fallback:** only if the heading matched *no* spec, fall back to matching anchors against the **body**. (Catches numeric-only headings and preamble.)
3. **Salary-grid rescue (remuneration only):** independently of 1–2, if the section contains a table that is *salary-grid-shaped* — a structural, keyword-independent test: **≥ 6 two-decimal money numbers** (`\b\d{1,3}[.,]\d{2}\b`) in the table content — assign the section to `remuneration`. This guarantees wage tables reach the salary pass even when the surrounding text uses no anchor. **When a section has no extracted tables** (inline-only OCR — empty `page.tables` with the wage data left in the markdown), the same money-number test is applied to the section **body** instead, so wage data is never lost to that OCR variant. The body branch is scoped to the no-tables case so the common path (tables populated, content also inlined in the body) does not over-recall prose money amounts.
4. **identity head:** always also include the preamble + first 3 sections (front matter: parties, looptijd).
5. **catch-all coverage:** any section still unassigned → the `supplementary` (catch-all) bundle.

The slice for a spec = its assigned sections' `text` (heading + body, tables already inlined in the body), concatenated in document order.

Anchors (empirically tuned against the Bouw CAO — over-broad terms removed: `cao`, `regeling`, `vergoeding` were each matching 80–280 sections):
- **identity:** `("looptijd", "werkingssfeer", "begrippen", "definities", "partijen")`.
- **remuneration:** `("salaris", "loon", "loontabel", "loonsverhoging", "functiegroep", "salarisschaal", "salarisgroep", "periodiek", "garantieloon", "uurloon")`.
- **allowances:** `("toeslag", "ort", "onregelmatig", "ploegen", "overwerk", "reiskosten", "vakantietoeslag", "vakantiegeld", "reisuren")`.
- **leave:** `("verlof", "vakantie", "adv", "atv", "feestdag", "ziekte", "arbeidsongeschikt", "roostervrije")`.
- **pension:** `("pensioen", "ikb", "keuzebudget", "generatiepact", "duurzame inzetbaarheid")`.
- **supplementary:** `is_catch_all=True`; anchors `("eenmalig", "uitkering", "bonus", "afbouw", "jubileum")`.

### Empirical validation (Bouw & Infra, 179 pages, on-disk `.ocr.json`)

The full routing was prototyped against the real document before committing to this design:
- **35/35 salary-grid tables route to `remuneration`** (heading-match + salary-grid rescue). The naive first cut (body matching + broad anchors) misrouted ~half the salary tables into `supplementary` via the `regeling` anchor catching "Basisregeling" — which is exactly the silent-failure case this design must prevent.
- Independent ground truth (functiegroep wage scale: A = `17,43` … `19,23`) is present in the `remuneration` slice.
- Slice sizes vs the full 387 KB: identity 27%, remuneration 52%, allowances 53%, leave 41%, pension 27%, supplementary 31%. No bundle falls back. The size win is real but **modest (~half)** — the primary value is correct routing (recall), not dramatic reduction.

## 7. Safety — "never worse than today"

- **Coverage guarantee:** after routing all specs, every `MappedSection` and `MappedTable` must be assigned to ≥1 spec. Any unassigned section → appended to the catch-all (`supplementary`) and logged. No content is silently dropped.
- **Empty-slice fallback (Rik: "veiligheid boven besparing"):** if a spec's assembled slice is empty or below a small char threshold, that pass receives the **whole document** (`doc_map.full_markdown()`), and `SectionRoutingInfo.fallback_used = True` is recorded + a warning logged. So a poor match never does worse than the current whole-doc behavior, and the fallback is **visible**, not masked.
- **Mapping failure:** the whole map+route block in the CLI is wrapped in try/except → on any error, fall back to `routed_inputs=None` (whole-doc for all passes) with a logged warning.
- **Legacy / missing `.ocr.json`:** fall back to whole-doc (warning logged).

## 8. Provenance interaction (Fase C)

Both the canonical Gemini pass and the independent Mistral pass **must receive the same `routed_inputs`**, so the inter-model agreement compares like-with-like (same input per section → the agreement signal stays honest). The provenance computation itself is unchanged.

## 9. Testing (TDD)

**Offline unit tests** (synthetic `OCRResult`s, no network):
- `build_document_map`: headings → ordered sections in document order; a table placeholder → its correct section; a page with no leading heading continues the previous section; text before the first heading → preamble; `page_start`/`page_end` correct; `full_markdown()` reproduces the content.
- `route_sections`: anchors select the right sections; a salary table routes to `remuneration`; unmatched section → catch-all (`supplementary`); coverage (no orphan sections/tables); empty slice → whole-doc fallback with `fallback_used=True`; a multi-match table appears in all matching slices.
- `gemini_sectioned.extract` with `routed_inputs`: each pass receives its routed slice (assert via a fake `generate` capturing the prompt); without `routed_inputs`, output is identical to current behavior.

**Integration test** on the real `data/ocr/488-bouw-...ocr.json` (on disk, no network):
- The `remuneration` slice contains the salary tables and is **dramatically smaller** than the full document (assert a meaningful size reduction); the `leave` slice contains verlof content; coverage holds (no orphans); report records per-section sizes.

**Online anchor smoke** (Fase E style, marked `online`): run sectioned + routing on a real CAO and assert ground-truth anchors still hit (e.g. ≥20 salary steps) — proving routing does not route the salary data away.

## 10. What stays untouched

OCR client (already captures everything needed), Fase E section schemas + `merge_sections`, Fase C provenance computation, the reviewer/judge-skip in sectioned mode, and the SETU output shape.

## 11. Resolved decisions

- **Approach A** (OCR maps structure; LLM maps to SETU) — confirmed.
- **Approach 1** (deterministic map + routing; no extra LLM pass) over semantic annotation (deferred) and native chunked annotation (rejected) — confirmed.
- **Empty-slice fallback to whole-doc** ("veiligheid boven besparing") + a visible warning flag — confirmed.
