# Fase E — Sectie-gewijze Gemini-extractie — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vervang de single-pass Gemini-extractie door 6 gefocuste sectie-passes (elk met een klein per-sectie `response_schema`) + een deterministische merge, zodat CAO's compleet én rijk naar SETU v2.0 worden geëxtraheerd.

**Architecture:** Per sectie één Gemini-call met een klein, ge-inlined, Gemini-veilig schema (bewezen op de salaris-sectie: 126 treden, API-geaccepteerd, past in budget). De 6 bundels bezitten disjuncte top-level SETU-keys → merge = key-union. Vervangt Step 1 in `extract_setu_pipeline`; Mistral-reviewer + judge blijven ongewijzigd.

**Tech Stack:** Python 3.11+, google-genai 1.66, pytest, structlog, ruff (line-length 100).

**Spec:** `docs/superpowers/specs/2026-06-06-cao-centraal-fase-e-sectioned-extraction-design.md`

> **Refinement t.o.v. spec:** de spec noemde een `build_section_schema`-transform mét hand-gebouwd schema als fallback. Dit plan kiest de **transform als primair** (DRY, SETU blijft bron-van-waarheid) en valideert per sectie (offline `t_schema` + online smoke). De spike-handbouw is de bewezen vorm die de transform reproduceert.

> **Branch:** verder op `feat/cao-centraal-provenance` (bevat de schema-loze extractor-basis die Fase E vervangt). Geen worktree nodig.

---

## File Structure

Nieuw pakket `src/cao_engine/extraction/sectioned/`:
- `__init__.py` — exports.
- `section_schema.py` — `build_section_schema(top_level_keys)`: bouwt een klein, ge-inlined, gestript, diepte-gecapt Gemini-veilig schema uit de rc.1-bundel. Pure functie.
- `sections.py` — `SectionSpec` dataclass + `SECTIONS` (de 6 bundels: key, top-level keys, prompt-focus). `SectionSpec.schema` roept `build_section_schema` aan; `SectionSpec.build_prompt(markdown, cao_name)`.
- `merge.py` — `merge_sections(slices)`: pure key-union van disjuncte slices.
- `gemini_sectioned.py` — `make_gemini_generate(...)` (echte API-caller via DI) + `SectionedGeminiExtractor` (orkestreert 6 passes, isoleert falen, merge).

Tests in `tests/sectioned/`: `test_section_schema.py`, `test_sections.py`, `test_merge.py`, `test_gemini_sectioned.py`, `test_online_validation.py`.

Wijzigen: `src/cao_engine/cli.py` (`extract_setu_pipeline` Step 1, achter `--sectioned`).

---

## Task 1: `build_section_schema` transform

**Files:**
- Create: `src/cao_engine/extraction/sectioned/__init__.py` (leeg)
- Create: `src/cao_engine/extraction/sectioned/section_schema.py`
- Test: `tests/sectioned/__init__.py` (leeg), `tests/sectioned/test_section_schema.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sectioned/test_section_schema.py
import copy
from cao_engine.extraction.sectioned.section_schema import build_section_schema


def test_remuneration_schema_is_gemini_safe_and_inlined():
    schema = build_section_schema(["remuneration"])
    blob = __import__("json").dumps(schema)
    assert schema["type"] == "object"
    assert "remuneration" in schema["properties"]
    # nothing the Gemini API rejects
    for forbidden in ("oneOf", "discriminator", "anyOf", "allOf",
                      "additionalProperties", "$ref", "$defs", "required"):
        assert f'"{forbidden}"' not in blob, forbidden


def test_built_schema_is_accepted_by_genai_sdk():
    from google.genai import _transformers
    schema = build_section_schema(["remuneration", "pension"])
    _transformers.t_schema(None, copy.deepcopy(schema))  # must not raise


def test_unknown_top_level_key_is_ignored():
    schema = build_section_schema(["remuneration", "doesNotExist"])
    assert "doesNotExist" not in schema["properties"]
    assert "remuneration" in schema["properties"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/sectioned/test_section_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: cao_engine.extraction.sectioned.section_schema`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cao_engine/extraction/sectioned/section_schema.py
"""Build a small, Gemini-safe response_schema for a set of top-level SETU keys.

The rc.1 SETU schema is a bundle of named types; the root is InquiryPayEquity and
refs are OpenAPI-style #/components/schemas/X. The Gemini API rejects oneOf,
discriminator, additionalProperties, deep nesting, and unresolved refs. This transform
slices the requested top-level properties, INLINES refs from the bundle, strips the
rejected keywords, and caps depth (which also breaks the recursive Condition type).
"""
import json
from pathlib import Path

_SCHEMA_PATH = (
    Path(__file__).parent.parent.parent / "compliance" / "schemas" / "setu_v2.0.0-rc.1.json"
)
_RC1 = json.loads(_SCHEMA_PATH.read_text())
_DEFS = dict(_RC1)  # all 89 named types resolve by name

_STRIP = ("$schema", "$id", "title", "description", "additionalProperties")
_POLY = ("oneOf", "anyOf", "allOf", "discriminator")
_MAX_DEPTH = 5


def _resolve(obj, depth):
    if depth >= _MAX_DEPTH:
        if isinstance(obj, dict) and obj.get("type") == "array":
            return {"type": "array", "items": {"type": "object"}}
        return {"type": "object"}
    if isinstance(obj, dict):
        if "$ref" in obj:
            name = obj["$ref"].split("/")[-1]
            target = _DEFS.get(name)
            return _resolve(target, depth + 1) if target is not None else {"type": "object"}
        if any(k in obj for k in _POLY):
            return {"type": "object"}
        out = {}
        for key, value in obj.items():
            if key in _STRIP:
                continue
            out[key] = _resolve(value, depth + 1) if isinstance(value, (dict, list)) else value
        req = out.get("required")
        if isinstance(req, list):
            props = out.get("properties")
            kept = [r for r in req if isinstance(props, dict) and r in props]
            if kept:
                out["required"] = kept
            else:
                out.pop("required", None)
        return out
    if isinstance(obj, list):
        return [_resolve(item, depth) for item in obj]
    return obj


def build_section_schema(top_level_keys: list[str]) -> dict:
    ipe_props = _RC1["InquiryPayEquity"]["properties"]
    props = {k: ipe_props[k] for k in top_level_keys if k in ipe_props}
    return _resolve({"type": "object", "properties": props}, 0)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/sectioned/test_section_schema.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/cao_engine/extraction/sectioned/__init__.py src/cao_engine/extraction/sectioned/section_schema.py tests/sectioned/__init__.py tests/sectioned/test_section_schema.py
git commit -m "feat: build_section_schema transform (Gemini-safe per-section schema)"
```

---

## Task 2: Section definitions (6 bundels)

**Files:**
- Create: `src/cao_engine/extraction/sectioned/sections.py`
- Test: `tests/sectioned/test_sections.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sectioned/test_sections.py
import copy
from cao_engine.extraction.sectioned.sections import SECTIONS

ALL_18 = {
    "documentId", "versionId", "issued", "effectivePeriod", "customer",
    "baseDefinition", "labourAgreements", "positionProfile", "remuneration",
    "allowance", "holidayAllowance", "sickPay", "leave", "individualChoiceBudget",
    "pension", "sustainableEmployability", "supplementaryArrangement", "otherArrangement",
}


def test_six_sections_cover_all_18_keys_disjointly():
    assert len(SECTIONS) == 6
    seen = []
    for spec in SECTIONS:
        seen.extend(spec.top_level_keys)
    assert sorted(seen) == sorted(ALL_18)          # cover everything
    assert len(seen) == len(set(seen))             # no overlap (disjoint)


def test_each_section_builds_a_gemini_safe_schema():
    from google.genai import _transformers
    for spec in SECTIONS:
        _transformers.t_schema(None, copy.deepcopy(spec.schema))  # must not raise


def test_build_prompt_includes_focus_and_markdown():
    spec = next(s for s in SECTIONS if s.key == "remuneration")
    prompt = spec.build_prompt("MARKDOWN_BODY", "IKEA CAO")
    assert "MARKDOWN_BODY" in prompt
    assert "IKEA CAO" in prompt
    assert spec.prompt_focus in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/sectioned/test_sections.py -v`
Expected: FAIL — `ModuleNotFoundError: ...sections`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cao_engine/extraction/sectioned/sections.py
"""The 6 extraction bundles. Each owns a disjoint set of top-level SETU keys."""
from dataclasses import dataclass, field

from cao_engine.extraction.sectioned.section_schema import build_section_schema

_BASE = (
    "You are extracting ONE part of a Dutch CAO into SETU v2.0 InquiryPayEquity JSON.\n"
    "Extract COMPLETELY and use EXACT Dutch terminology from the CAO. Do NOT summarize.\n"
    "Use null for unknown fields. Only output the part described below.\n"
)


@dataclass(frozen=True)
class SectionSpec:
    key: str
    top_level_keys: list[str]
    prompt_focus: str
    schema: dict = field(default=None)

    def __post_init__(self):
        # frozen dataclass: set schema via object.__setattr__
        object.__setattr__(self, "schema", build_section_schema(self.top_level_keys))

    def build_prompt(self, markdown: str, cao_name: str | None) -> str:
        return (
            f"{_BASE}\nFOCUS: {self.prompt_focus}\n\n"
            f"CAO Name: {cao_name or 'Unknown'}\n\n"
            f"COMPLETE CAO Document (Markdown from Mistral OCR):\n\n{markdown}"
        )


SECTIONS: list[SectionSpec] = [
    SectionSpec(
        key="identity",
        top_level_keys=["documentId", "versionId", "issued", "effectivePeriod",
                        "customer", "labourAgreements", "positionProfile", "baseDefinition"],
        prompt_focus=("Document identity & parties: documentId, versionId, issued date, "
                      "effectivePeriod (validFrom/validTo), customer (employer name + legalId/KvK), "
                      "labourAgreements, positionProfile(s) and baseDefinition(s)."),
    ),
    SectionSpec(
        key="remuneration",
        top_level_keys=["remuneration"],
        prompt_focus=("Salary structure: remuneration[].salaryScale[] = each functiegroep/schaal "
                      "(name, minValue, maxValue, currency); salaryScale[].salaryStep[] = EVERY trede "
                      "(name, value=bruto EUR amount); generalSalaryIncrease[] = each algemene "
                      "loonsverhoging (effectivePeriod.validFrom, percentage). A CAO has many scales "
                      "each with many steps."),
    ),
    SectionSpec(
        key="allowances",
        top_level_keys=["allowance", "holidayAllowance"],
        prompt_focus=("Allowances: allowance[] = every toeslag (ORT, ploegentoeslag, overwerk, "
                      "reiskosten, etc.); holidayAllowance[] = vakantietoeslag (percentage + payment "
                      "moment)."),
    ),
    SectionSpec(
        key="leave",
        top_level_keys=["leave", "sickPay"],
        prompt_focus=("Leave & sick pay: leave[] = ADV/ATV, verlof, feestdagen, bijzonder verlof; "
                      "sickPay[] = loondoorbetaling bij ziekte."),
    ),
    SectionSpec(
        key="pension",
        top_level_keys=["pension", "individualChoiceBudget", "sustainableEmployability"],
        prompt_focus=("Pension & budgets: pension[] = pensioenregeling(en) offered by the employer "
                      "(fund name, origin, contribution split); individualChoiceBudget[] = IKB; "
                      "sustainableEmployability[] = duurzame inzetbaarheid / generatiepact."),
    ),
    SectionSpec(
        key="supplementary",
        top_level_keys=["supplementaryArrangement", "otherArrangement"],
        prompt_focus=("Supplementary: supplementaryArrangement[] = eenmalige uitkeringen, bonussen, "
                      "afbouwregelingen; otherArrangement[] = remaining arrangements not covered above."),
    ),
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/sectioned/test_sections.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/cao_engine/extraction/sectioned/sections.py tests/sectioned/test_sections.py
git commit -m "feat: 6 disjoint section specs with focused prompts"
```

---

## Task 3: `merge_sections` (pure)

**Files:**
- Create: `src/cao_engine/extraction/sectioned/merge.py`
- Test: `tests/sectioned/test_merge.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sectioned/test_merge.py
from cao_engine.extraction.sectioned.merge import merge_sections


def test_disjoint_slices_union_into_one_doc():
    slices = [
        {"documentId": {"value": "X"}, "customer": {"name": "IKEA"}},
        {"remuneration": [{"salaryScale": [{"name": "A"}]}]},
        {"pension": [{"name": "PF"}]},
    ]
    merged = merge_sections(slices)
    assert merged["documentId"] == {"value": "X"}
    assert merged["customer"] == {"name": "IKEA"}
    assert merged["remuneration"] == [{"salaryScale": [{"name": "A"}]}]
    assert merged["pension"] == [{"name": "PF"}]


def test_empty_and_none_slices_are_skipped():
    merged = merge_sections([{"leave": [1]}, {}, None])
    assert merged == {"leave": [1]}


def test_later_nonempty_value_wins_on_key_collision():
    # disjoint by design, but be deterministic if it happens: last non-empty wins
    merged = merge_sections([{"pension": []}, {"pension": [{"name": "PF"}]}])
    assert merged["pension"] == [{"name": "PF"}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/sectioned/test_merge.py -v`
Expected: FAIL — `ModuleNotFoundError: ...merge`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cao_engine/extraction/sectioned/merge.py
"""Deterministic key-union of disjoint section slices into one InquiryPayEquity dict."""


def _empty(value) -> bool:
    return value is None or value == {} or value == []


def merge_sections(slices: list[dict | None]) -> dict:
    merged: dict = {}
    for slice_ in slices:
        if not slice_:
            continue
        for key, value in slice_.items():
            if _empty(value):
                continue
            merged[key] = value  # last non-empty wins (slices are disjoint by design)
    return merged
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/sectioned/test_merge.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/cao_engine/extraction/sectioned/merge.py tests/sectioned/test_merge.py
git commit -m "feat: deterministic merge_sections for disjoint slices"
```

---

## Task 4: `SectionedGeminiExtractor` (orchestrator, DI)

**Files:**
- Create: `src/cao_engine/extraction/sectioned/gemini_sectioned.py`
- Test: `tests/sectioned/test_gemini_sectioned.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sectioned/test_gemini_sectioned.py
import json

from cao_engine.extraction.sectioned.gemini_sectioned import SectionedGeminiExtractor
from cao_engine.extraction.sectioned.sections import SectionSpec


def _spec(key, keys):
    return SectionSpec(key=key, top_level_keys=keys, prompt_focus=f"focus {key}")


def test_runs_each_section_and_merges_slices():
    sections = [_spec("identity", ["documentId"]), _spec("remuneration", ["remuneration"])]
    returns = {
        "identity": (json.dumps({"documentId": {"value": "X"}}), "STOP"),
        "remuneration": (json.dumps({"remuneration": [{"salaryScale": []}]}), "STOP"),
    }
    calls = []

    def fake_generate(prompt, schema):
        # identify section by which focus is in the prompt
        key = "identity" if "focus identity" in prompt else "remuneration"
        calls.append(key)
        return returns[key]

    extractor = SectionedGeminiExtractor(fake_generate, sections=sections)
    result = extractor.extract("MD", "CAO")

    assert calls == ["identity", "remuneration"]
    assert result["documentId"] == {"value": "X"}
    assert result["remuneration"] == [{"salaryScale": []}]
    assert result["_section_meta"]["identity"]["ok"] is True
    assert result["_section_meta"]["remuneration"]["finish"] == "STOP"


def test_failing_section_is_isolated():
    sections = [_spec("identity", ["documentId"]), _spec("remuneration", ["remuneration"])]

    def fake_generate(prompt, schema):
        if "focus remuneration" in prompt:
            raise RuntimeError("API 500")
        return json.dumps({"documentId": {"value": "X"}}), "STOP"

    result = SectionedGeminiExtractor(fake_generate, sections=sections).extract("MD", "CAO")
    assert result["documentId"] == {"value": "X"}          # good section survived
    assert result["_section_meta"]["remuneration"]["ok"] is False
    assert "API 500" in result["_section_meta"]["remuneration"]["error"]


def test_bad_json_is_isolated():
    sections = [_spec("identity", ["documentId"])]

    def fake_generate(prompt, schema):
        return "{not valid json", "STOP"

    result = SectionedGeminiExtractor(fake_generate, sections=sections).extract("MD", "CAO")
    assert result["_section_meta"]["identity"]["ok"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/sectioned/test_gemini_sectioned.py -v`
Expected: FAIL — `ModuleNotFoundError: ...gemini_sectioned`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cao_engine/extraction/sectioned/gemini_sectioned.py
"""Sectioned Gemini extraction: one focused pass per bundle, then merge.

generate is injected (DI) so the orchestration is testable without the SDK:
    generate(prompt: str, schema: dict) -> tuple[json_text: str, finish_reason: str]
"""
import json
from collections.abc import Callable

import structlog

from cao_engine.extraction.sectioned.merge import merge_sections
from cao_engine.extraction.sectioned.sections import SECTIONS, SectionSpec

logger = structlog.get_logger(__name__)

GenerateFn = Callable[[str, dict], tuple[str, str]]


class SectionedGeminiExtractor:
    def __init__(self, generate: GenerateFn, sections: list[SectionSpec] = SECTIONS) -> None:
        self._generate = generate
        self._sections = sections

    def extract(self, markdown: str, cao_name: str | None = None) -> dict:
        slices: list[dict] = []
        meta: dict = {}
        for spec in self._sections:
            try:
                text, finish = self._generate(spec.build_prompt(markdown, cao_name), spec.schema)
                data = json.loads(text)
                slices.append(data)
                meta[spec.key] = {"ok": True, "finish": finish}
                logger.info("section extracted", section=spec.key, finish=finish)
            except Exception as exc:  # API error, JSON parse, etc. -> isolate
                meta[spec.key] = {"ok": False, "error": str(exc)}
                logger.warning("section failed", section=spec.key, error=str(exc))
        merged = merge_sections(slices)
        merged["_section_meta"] = meta
        return merged


def make_gemini_generate(api_key: str, model: str, thinking_level: str = "LOW") -> GenerateFn:
    """Real generate fn backed by google-genai (schema-constrained, capped output)."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    level = getattr(types.ThinkingLevel, thinking_level.upper(), types.ThinkingLevel.LOW)

    def generate(prompt: str, schema: dict) -> tuple[str, str]:
        config = types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=schema,
            max_output_tokens=65536,
            thinking_config=types.ThinkingConfig(thinking_level=level, include_thoughts=False),
        )
        response = client.models.generate_content(model=model, contents=prompt, config=config)
        finish = str(response.candidates[0].finish_reason)
        return response.text or "", finish

    return generate
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/sectioned/test_gemini_sectioned.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/cao_engine/extraction/sectioned/gemini_sectioned.py tests/sectioned/test_gemini_sectioned.py
git commit -m "feat: SectionedGeminiExtractor with DI and failure isolation"
```

---

## Task 5: Wire into `extract_setu_pipeline` behind `--sectioned`

**Files:**
- Modify: `src/cao_engine/cli.py` (the `extract_setu_pipeline` command + Step 1)
- Modify: `src/cao_engine/extraction/sectioned/__init__.py` (exports)

- [ ] **Step 1: Add exports (no test — re-export only)**

```python
# src/cao_engine/extraction/sectioned/__init__.py
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
]
```

- [ ] **Step 2: Add the `--sectioned` option and swap Step 1**

In `src/cao_engine/cli.py`, add the option to `extract_setu_pipeline`'s signature:

```python
    sectioned: bool = typer.Option(
        False, "--sectioned", help="Use 6-pass sectioned Gemini extraction (Fase E)"
    ),
```

Replace the Step 1 block (currently `gemini = GeminiPrimaryExtractor(...)` / `gemini_output = gemini.extract(...)`) with:

```python
    # Step 1: Gemini Primary Extraction
    console.print(f"[bold]Step 1/3:[/bold] {settings.gemini_model} (Primary Extractor)")
    if sectioned:
        from cao_engine.extraction.sectioned import (
            SectionedGeminiExtractor,
            make_gemini_generate,
        )
        console.print("[dim]  Mode: sectioned (6 passes)[/dim]")
        generate = make_gemini_generate(
            settings.google_api_key, settings.gemini_model, settings.gemini_thinking_level
        )
        gemini_output = SectionedGeminiExtractor(generate).extract(markdown_text, cao)
    else:
        from cao_engine.extraction.gemini_primary import GeminiPrimaryExtractor
        console.print(f"[dim]  Thinking level: {settings.gemini_thinking_level}[/dim]")
        gemini = GeminiPrimaryExtractor(
            settings.google_api_key, settings.gemini_model, settings.gemini_thinking_level
        )
        gemini_output = gemini.extract(markdown_text, cao)
```

(Leave the existing `from ... import GeminiPrimaryExtractor` at the top of the function; the inline imports above shadow nothing harmful — if a top-level import exists, remove it to avoid an unused import per ruff.)

- [ ] **Step 3: Verify the CLI imports and help work**

Run: `python3 -m cao_engine extract-setu-pipeline --help`
Expected: help text shows the `--sectioned` flag, no import errors.

- [ ] **Step 4: Run the full sectioned package test suite + ruff**

Run: `python3 -m pytest tests/sectioned/ -q && python3 -m ruff check src/cao_engine/extraction/sectioned/ tests/sectioned/`
Expected: all green, ruff clean on new files.

- [ ] **Step 5: Commit**

```bash
git add src/cao_engine/extraction/sectioned/__init__.py src/cao_engine/cli.py
git commit -m "feat: --sectioned flag wires SectionedGeminiExtractor into the pipeline"
```

---

## Task 6: Online validation against ground-truth anchors

Validates the hypothesis on real CAOs. Marked `online` so it is skipped by default (needs `GOOGLE_API_KEY` + costs money). This is the gate that confirms all 6 bundles work — not just remuneration.

**Files:**
- Create: `tests/sectioned/test_online_validation.py`
- Modify: `pyproject.toml` (register the `online` marker if not present)

- [ ] **Step 1: Register the marker**

In `pyproject.toml`, under `[tool.pytest.ini_options]` add (or extend) markers:

```toml
markers = [
    "online: tests that hit live LLM APIs (skipped by default; run with -m online)",
]
```

- [ ] **Step 2: Write the online validation test**

```python
# tests/sectioned/test_online_validation.py
import os
from pathlib import Path

import pytest

from cao_engine.extraction.sectioned import SectionedGeminiExtractor, make_gemini_generate

pytestmark = pytest.mark.online

OCR = Path("data/ocr/1049-ikea-cao-1-10-2023-tm-31-12-2024-v07022024.md")


@pytest.mark.skipif(not os.environ.get("GOOGLE_API_KEY"), reason="no GOOGLE_API_KEY")
def test_ikea_sectioned_extraction_hits_ground_truth_anchors():
    markdown = OCR.read_text(encoding="utf-8")
    generate = make_gemini_generate(os.environ["GOOGLE_API_KEY"], "gemini-3.5-flash", "LOW")
    doc = SectionedGeminiExtractor(generate).extract(markdown, "IKEA CAO 2023-2024")

    # every section completed
    assert all(m["ok"] for m in doc["_section_meta"].values()), doc["_section_meta"]

    # ground-truth anchors pulled from the ikea OCR (not leaf-count vs another model)
    import json as _json
    blob = _json.dumps(doc, ensure_ascii=False).lower()
    assert "ikea" in _json.dumps(doc.get("customer", {}), ensure_ascii=False).lower()
    assert "2023-10-01" in _json.dumps(doc.get("effectivePeriod", {}))
    assert "2024-12-31" in _json.dumps(doc.get("effectivePeriod", {}))
    assert doc.get("holidayAllowance"), "vakantietoeslag missing"
    assert doc.get("pension"), "pension missing"

    # richness: many salary steps (spike got 126)
    steps = [s for pkg in doc.get("remuneration", [])
             for sc in pkg.get("salaryScale", []) for s in sc.get("salaryStep", [])]
    assert len(steps) >= 20, f"only {len(steps)} salary steps"
```

- [ ] **Step 3: Run it (online, costs money)**

Run: `python3 -m pytest tests/sectioned/test_online_validation.py -m online -v`
Expected: PASS — all sections ok, anchors hit, ≥20 salary steps.

If a section fails or under-extracts: hand-tune that section's `prompt_focus` or `top_level_keys`, or lower `_MAX_DEPTH`/split the bundle; re-run. (This is the per-bundle validation the design calls for.)

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml tests/sectioned/test_online_validation.py
git commit -m "test: online validation of sectioned extraction against ground-truth anchors"
```

---

## Self-Review

- **Spec coverage:** §3 dataflow → Task 4/5; §4 six bundels → Task 2; §5 components → Tasks 1-4 (section_schema, sections, merge, gemini_sectioned); §6 failure-isolatie → Task 4; §7 testen → Tasks 1-3 unit + Task 6 online anchors; §8 integratie/scope → Task 5 (reviewer/judge untouched). The spec's `GeminiSectionPass` class is folded into the orchestrator loop (YAGNI) — noted in File Structure.
- **Placeholder scan:** none — every code step has complete code; the only deferred decision (per-bundle prompt tuning) lives in Task 6 Step 3 with a concrete procedure.
- **Type consistency:** `build_section_schema(list[str])`, `SectionSpec(key, top_level_keys, prompt_focus, schema)`, `merge_sections(list)`, `SectionedGeminiExtractor(generate, sections)`, `GenerateFn = (prompt, schema) -> (text, finish)`, `make_gemini_generate(api_key, model, thinking_level)` are used consistently across tasks.
