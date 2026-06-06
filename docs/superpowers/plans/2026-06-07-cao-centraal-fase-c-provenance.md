# Fase C — Provenance uit inter-model agreement — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bereken een eerlijk, per-sectie inter-model agreement-signaal (Gemini-sectioned vs onafhankelijke Mistral-sectioned) en schrijf het naar de provenance-sidecar die de read-side al leest.

**Architecture:** Mistral draait dezelfde 6 sectie-passes als Gemini (DI: `make_mistral_generate` hergebruikt `SectionedGeminiExtractor` + dezelfde sectie-schemas — spike-bevestigd dat Mistral die strict accepteert). Een pure `agreement`-module vergelijkt de twee complete docs per sectie (genormaliseerd: NL-bedragen, casing, datums). Het resultaat gaat in een uitgebreide `Provenance{sections}` sidecar. Opt-in via `--provenance`.

**Tech Stack:** Python 3.11+, mistralai SDK, google-genai, pytest, structlog, ruff (line-length 100).

**Spec:** `docs/superpowers/specs/2026-06-07-cao-centraal-fase-c-provenance-design.md`

> **Linchpin RESOLVED (spike 2026-06-07):** Mistral `mistral-large-latest` accepteert onze Gemini-veilige sectie-schemas via `response_format={"type":"json_schema","json_schema":{...,"strict":True}}` en levert vergelijkbare structuur (10 scales/60 steps op ikea vs Gemini 26/126). Geen Mistral-specifieke schema-transform nodig.

> **Branch:** `feat/cao-centraal-fase-c` (vanaf Fase E-HEAD). Bouwt op het `sectioned`-pakket.

---

## File Structure

- `src/cao_engine/extraction/sectioned/mistral_sectioned.py` (new) — `make_mistral_generate(api_key, model)`: Mistral-backed `generate(prompt, schema) -> (text, finish)` voor de bestaande `SectionedGeminiExtractor`.
- `src/cao_engine/provenance/agreement.py` (new) — pure agreement-berekening: `normalize_value`, `section_agreement`, `compute_agreement`.
- `src/cao_engine/serving/provenance.py` (modify) — `Provenance` krijgt `sections` veld.
- `src/cao_engine/serving/provenance_writer.py` (new) — `write_provenance(...)`.
- `src/cao_engine/cli.py` (modify) — `--provenance` flag in `extract_setu_pipeline`.
- Tests: `tests/provenance/test_agreement.py`, `tests/provenance/test_provenance_writer.py`, `tests/sectioned/test_online_validation.py` (extend).

> Note: `agreement.py` + `provenance_writer.py` live under a new `src/cao_engine/provenance/` package (agreement is a serving/quality concern, not an extraction concern). `Provenance` model stays in `serving/` where the read-side already imports it.

---

## Task 1: `make_mistral_generate` (independent Mistral sectioned extraction)

**Files:**
- Create: `src/cao_engine/extraction/sectioned/mistral_sectioned.py`
- Test: `tests/sectioned/test_mistral_sectioned.py`

- [ ] **Step 1: Write the failing test** (verifies the factory returns a callable with the right shape; the live call is covered by the online test in Task 5)

```python
from cao_engine.extraction.sectioned.mistral_sectioned import make_mistral_generate


def test_factory_returns_callable():
    generate = make_mistral_generate("dummy-key", "mistral-large-latest")
    assert callable(generate)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/sectioned/test_mistral_sectioned.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cao_engine/extraction/sectioned/mistral_sectioned.py
"""Independent Mistral sectioned extraction for inter-model agreement (Fase C).

Mistral runs the SAME 6 section passes as Gemini, with the SAME section schemas
(spike-confirmed: Mistral accepts them via strict json_schema). It does NOT see
Gemini's output -> the two extractions are independent. Provides a `generate`
callable for the model-agnostic SectionedGeminiExtractor.
"""
from collections.abc import Callable

GenerateFn = Callable[[str, dict], tuple[str, str]]


def make_mistral_generate(api_key: str, model: str = "mistral-large-latest") -> GenerateFn:
    from mistralai import Mistral

    client = Mistral(api_key=api_key)

    def generate(prompt: str, schema: dict) -> tuple[str, str]:
        response = client.chat.complete(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "section", "schema": schema, "strict": True},
            },
            temperature=0.1,
        )
        choice = response.choices[0]
        return choice.message.content or "", str(choice.finish_reason)

    return generate
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/sectioned/test_mistral_sectioned.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/cao_engine/extraction/sectioned/mistral_sectioned.py tests/sectioned/test_mistral_sectioned.py
git commit -m "feat: make_mistral_generate for independent sectioned extraction"
```

---

## Task 2: `agreement.py` — value normalization

**Files:**
- Create: `src/cao_engine/provenance/__init__.py` (empty), `src/cao_engine/provenance/agreement.py`
- Test: `tests/provenance/__init__.py` (empty), `tests/provenance/test_agreement.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/provenance/test_agreement.py
from cao_engine.provenance.agreement import normalize_value


def test_dutch_money_normalizes_to_plain_number():
    assert normalize_value("€ 1.500,00") == normalize_value("1500") == normalize_value(1500.0)


def test_decimal_comma_normalizes():
    assert normalize_value("14,25") == normalize_value(14.25)


def test_strings_are_case_and_space_insensitive():
    assert normalize_value("  Functiegroep A ") == normalize_value("functiegroep a")


def test_none_and_bool():
    assert normalize_value(None) == "∅"
    assert normalize_value(True) == "true"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/provenance/test_agreement.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cao_engine/provenance/agreement.py
"""Deterministic inter-model agreement: how often two extractions match, per section.

Honest signal, NOT a correctness claim. Normalization absorbs cosmetic differences
(Dutch money formatting, casing, whitespace) so the ratio reflects real disagreement,
not formatting noise.
"""
import re

_NUM_THOUSANDS = re.compile(r"-?\d{1,3}(\.\d{3})+(,\d+)?$")  # 1.500,00
_NUM_DECIMAL_COMMA = re.compile(r"-?\d+,\d+$")               # 14,25


def normalize_value(value) -> str:
    if value is None:
        return "∅"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return f"{float(value):.4f}".rstrip("0").rstrip(".")
    text = str(value).strip().lower()
    money = re.sub(r"[^\d.,-]", "", text.replace("€", "").replace("eur", ""))
    if _NUM_THOUSANDS.fullmatch(money):
        money = money.replace(".", "").replace(",", ".")
    elif _NUM_DECIMAL_COMMA.fullmatch(money):
        money = money.replace(",", ".")
    try:
        return f"{float(money):.4f}".rstrip("0").rstrip(".")
    except ValueError:
        return text
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/provenance/test_agreement.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/cao_engine/provenance/__init__.py src/cao_engine/provenance/agreement.py tests/provenance/__init__.py tests/provenance/test_agreement.py
git commit -m "feat: normalize_value for agreement (Dutch money, casing)"
```

---

## Task 3: `agreement.py` — section & document agreement

**Files:**
- Modify: `src/cao_engine/provenance/agreement.py`
- Test: `tests/provenance/test_agreement.py`

- [ ] **Step 1: Write the failing test** (append)

```python
from cao_engine.provenance.agreement import compute_agreement, section_agreement


def test_identical_slices_agree_fully():
    a = {"remuneration": [{"salaryScale": [{"name": "A", "value": 14.25}]}]}
    assert section_agreement(a, dict(a)) == 1.0


def test_disjoint_slices_do_not_agree():
    a = {"leave": [{"name": "ADV"}]}
    b = {"leave": [{"name": "Vakantie"}]}
    assert section_agreement(a, b) == 0.0


def test_formatting_difference_still_agrees():
    a = {"pension": [{"amount": "1.500,00"}]}
    b = {"pension": [{"amount": 1500}]}
    assert section_agreement(a, b) == 1.0


def test_empty_both_sides_is_unmeasurable_none():
    assert section_agreement({}, {}) is None


def test_compute_agreement_returns_ratio_per_section():
    from cao_engine.extraction.sectioned.sections import SECTIONS
    gemini = {"remuneration": [{"salaryScale": [{"name": "A"}]}], "pension": [{"name": "PF"}]}
    mistral = {"remuneration": [{"salaryScale": [{"name": "A"}]}], "pension": [{"name": "XX"}]}
    result = compute_agreement(gemini, mistral, SECTIONS)
    assert result["remuneration"] == 1.0
    assert result["pension"] == 0.0
    assert result["leave"] is None  # neither doc has leave keys
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/provenance/test_agreement.py -v`
Expected: FAIL — `ImportError: cannot import name 'section_agreement'`

- [ ] **Step 3: Write minimal implementation** (append to `agreement.py`)

```python
def _flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key.startswith("_"):
                continue
            path = f"{prefix}.{key}" if prefix else key
            out.update(_flatten(value, path))
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            out.update(_flatten(value, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def section_agreement(slice_a: dict, slice_b: dict) -> float | None:
    """Matched / union of leaf paths, normalized. None when there is nothing to compare."""
    leaves_a = _flatten(slice_a)
    leaves_b = _flatten(slice_b)
    paths = set(leaves_a) | set(leaves_b)
    if not paths:
        return None
    matched = sum(
        1
        for p in paths
        if p in leaves_a
        and p in leaves_b
        and normalize_value(leaves_a[p]) == normalize_value(leaves_b[p])
    )
    return matched / len(paths)


def compute_agreement(gemini_doc: dict, mistral_doc: dict, sections) -> dict:
    """Per-section agreement ratio (or None if unmeasurable) keyed by section.key."""
    result = {}
    for spec in sections:
        gemini_slice = {k: gemini_doc[k] for k in spec.top_level_keys if k in gemini_doc}
        mistral_slice = {k: mistral_doc[k] for k in spec.top_level_keys if k in mistral_doc}
        result[spec.key] = section_agreement(gemini_slice, mistral_slice)
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/provenance/test_agreement.py -v`
Expected: PASS (9 tests total)

- [ ] **Step 5: Commit**

```bash
git add src/cao_engine/provenance/agreement.py tests/provenance/test_agreement.py
git commit -m "feat: section_agreement + compute_agreement (per-section, union leaf-diff)"
```

---

## Task 4: Extend `Provenance` + provenance writer

**Files:**
- Modify: `src/cao_engine/serving/provenance.py`
- Create: `src/cao_engine/provenance/provenance_writer.py`
- Test: `tests/provenance/test_provenance_writer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/provenance/test_provenance_writer.py
import json

from cao_engine.serving.provenance import Provenance, ProvenanceStore
from cao_engine.provenance.provenance_writer import write_provenance


def test_writes_sidecar_with_sections_and_mean_confidence(tmp_path):
    write_provenance("1049-ikea", {"remuneration": 0.8, "pension": 0.6, "leave": None}, tmp_path)
    prov = ProvenanceStore(tmp_path).get("1049-ikea")
    assert prov.source == "inter_model_agreement"
    assert prov.status == "unverified"
    assert prov.sections == {"remuneration": 0.8, "pension": 0.6}  # None dropped
    assert abs(prov.confidence - 0.7) < 1e-9  # mean of measurable sections


def test_skips_test_artifacts(tmp_path):
    write_provenance("test_tiny", {"remuneration": 1.0}, tmp_path)
    assert not (tmp_path / "test_tiny.provenance.json").exists()


def test_all_none_writes_no_confidence(tmp_path):
    write_provenance("1049-ikea", {"leave": None}, tmp_path)
    data = json.loads((tmp_path / "1049-ikea.provenance.json").read_text())
    assert data["confidence"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/provenance/test_provenance_writer.py -v`
Expected: FAIL — `ImportError` (sections field / writer missing)

- [ ] **Step 3a: Extend `Provenance`** in `src/cao_engine/serving/provenance.py`

Change the model class body to add the field (keep the rest of the file unchanged):

```python
class Provenance(BaseModel):
    """Correctness-labeling for a CAO document or component."""

    model_config = ConfigDict(frozen=True)

    status: Literal["verified", "unverified"] = "unverified"
    source: str = Field(default="ai_extracted", description="How the data was produced")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    sections: dict[str, float] | None = Field(
        default=None, description="Per-section inter-model agreement ratios"
    )
```

- [ ] **Step 3b: Write the writer** `src/cao_engine/provenance/provenance_writer.py`

```python
"""Write the provenance sidecar from computed inter-model agreement (Fase C)."""
from pathlib import Path

from cao_engine.serving._paths import is_safe_cao_id
from cao_engine.serving.provenance import Provenance


def write_provenance(cao_id: str, sections_agreement: dict, provenance_dir: Path) -> Path | None:
    """Write {cao_id}.provenance.json from per-section agreement. Returns the path,
    or None if skipped (unsafe id or test artifact)."""
    if not is_safe_cao_id(cao_id) or cao_id.startswith("test_"):
        return None
    measured = {k: v for k, v in sections_agreement.items() if v is not None}
    confidence = sum(measured.values()) / len(measured) if measured else None
    prov = Provenance(
        status="unverified",
        source="inter_model_agreement",
        confidence=confidence,
        sections=measured or None,
    )
    provenance_dir.mkdir(parents=True, exist_ok=True)
    path = provenance_dir / f"{cao_id}.provenance.json"
    path.write_text(prov.model_dump_json(indent=2), encoding="utf-8")
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/provenance/test_provenance_writer.py tests/serving/test_serving_provenance.py -v`
Expected: PASS (3 new + existing provenance tests still green)

- [ ] **Step 5: Commit**

```bash
git add src/cao_engine/serving/provenance.py src/cao_engine/provenance/provenance_writer.py tests/provenance/test_provenance_writer.py
git commit -m "feat: Provenance.sections + write_provenance sidecar writer"
```

---

## Task 5: Wire `--provenance` into the pipeline + online validation

**Files:**
- Modify: `src/cao_engine/cli.py` (`extract_setu_pipeline`)
- Test: `tests/sectioned/test_online_validation.py` (extend)

- [ ] **Step 1: Add the `--provenance` option** to `extract_setu_pipeline`'s signature (after `sectioned`):

```python
    provenance: bool = typer.Option(
        False, "--provenance",
        help="Also run independent Mistral-sectioned + write inter-model agreement (needs --sectioned)",
    ),
```

- [ ] **Step 2: After the final SETU is saved, add the provenance block.** Insert just before the closing `console.print(Panel(...))` of `extract_setu_pipeline`:

```python
    # Fase C: independent second extraction -> per-section inter-model agreement
    if provenance:
        if not sectioned:
            console.print("[yellow]--provenance requires --sectioned; skipping[/yellow]")
        else:
            from cao_engine.extraction.sectioned import SectionedGeminiExtractor
            from cao_engine.extraction.sectioned.mistral_sectioned import make_mistral_generate
            from cao_engine.provenance.agreement import compute_agreement
            from cao_engine.provenance.provenance_writer import write_provenance
            from cao_engine.extraction.sectioned.sections import SECTIONS

            console.print("[bold]Provenance:[/bold] independent Mistral-sectioned extraction")
            m_generate = make_mistral_generate(settings.mistral_api_key, settings.extraction_model)
            mistral_doc = SectionedGeminiExtractor(m_generate).extract(markdown_text, cao)
            agreement = compute_agreement(gemini_output, mistral_doc, SECTIONS)
            sidecar = write_provenance(
                ocr_path.stem, agreement, settings.data_dir / "provenance"
            )
            console.print(f"  Agreement per section: {agreement}")
            if sidecar:
                console.print(f"  ✓ Provenance: {sidecar.relative_to(settings.data_dir)}")
```

> Use `settings.data_dir / "provenance"` — this is exactly the path the read-side
> uses (`cao_service.py:37` constructs `ProvenanceStore(settings.data_dir / "provenance")`),
> so writer and reader agree. `write_provenance` mkdirs it; no config change needed.

- [ ] **Step 3: Verify CLI help + offline suite**

Run: `python3 -m cao_engine extract-setu-pipeline --help` (shows `--provenance`)
Run: `python3 -m pytest tests/provenance/ tests/sectioned/ -q -m "not online"`
Run: `python3 -m ruff check src/cao_engine/provenance/ src/cao_engine/extraction/sectioned/mistral_sectioned.py`
Expected: help shows flag; all offline tests pass; ruff clean.

- [ ] **Step 4: Extend the online validation test** in `tests/sectioned/test_online_validation.py` (append):

```python
@pytest.mark.skipif(not os.environ.get("GOOGLE_API_KEY") or not os.environ.get("MISTRAL_API_KEY"),
                    reason="needs GOOGLE_API_KEY and MISTRAL_API_KEY")
def test_ikea_inter_model_agreement_is_sane():
    from cao_engine.extraction.sectioned import SectionedGeminiExtractor, make_gemini_generate
    from cao_engine.extraction.sectioned.mistral_sectioned import make_mistral_generate
    from cao_engine.extraction.sectioned.sections import SECTIONS
    from cao_engine.provenance.agreement import compute_agreement

    markdown = OCR.read_text(encoding="utf-8")
    gemini = SectionedGeminiExtractor(
        make_gemini_generate(os.environ["GOOGLE_API_KEY"], "gemini-3.5-flash", "LOW")
    ).extract(markdown, "IKEA CAO 2023-2024")
    mistral = SectionedGeminiExtractor(
        make_mistral_generate(os.environ["MISTRAL_API_KEY"], "mistral-large-latest")
    ).extract(markdown, "IKEA CAO 2023-2024")

    agreement = compute_agreement(gemini, mistral, SECTIONS)
    measured = {k: v for k, v in agreement.items() if v is not None}
    assert measured, "no section was measurable"
    assert all(0.0 <= v <= 1.0 for v in measured.values()), agreement
    # identity (documentId/customer/period) should agree more than salaries (model-variable)
    assert measured.get("identity", 0) > 0.3, agreement
```

- [ ] **Step 5: Run online validation (costs money: Gemini + Mistral, 12 calls)**

Run: `python3 -m pytest tests/sectioned/test_online_validation.py::test_ikea_inter_model_agreement_is_sane -m online -v`
Expected: PASS — measurable sections, ratios in [0,1], identity agreement > 0.3.

- [ ] **Step 6: Commit**

```bash
git add src/cao_engine/cli.py tests/sectioned/test_online_validation.py
git commit -m "feat: --provenance wires inter-model agreement into the pipeline"
```

---

## Task 6: Backfill the 4 ground-truth CAOs

**Files:**
- Create: `scripts/backfill_provenance.py`

- [ ] **Step 1: Write the backfill script**

```python
# scripts/backfill_provenance.py
"""Backfill provenance sidecars for the ground-truth CAOs by running BOTH models
sectioned and computing per-section agreement. Run: python3 scripts/backfill_provenance.py"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from cao_engine.config import Settings
from cao_engine.extraction.sectioned import SectionedGeminiExtractor, make_gemini_generate
from cao_engine.extraction.sectioned.mistral_sectioned import make_mistral_generate
from cao_engine.extraction.sectioned.sections import SECTIONS
from cao_engine.provenance.agreement import compute_agreement
from cao_engine.provenance.provenance_writer import write_provenance

STEMS = [
    "1004-achmea-cao-01-12-2023-tm-31-08-2025-vbest27062024",
    "1006-groothandel-in-bloemen-en-planten-vgb-cao-2024-2026-v08042025",
    "1049-ikea-cao-1-10-2023-tm-31-12-2024-v07022024",
    "1055-rabobank-cao-2024-2025-v01102024",
]


def main() -> None:
    settings = Settings()
    provenance_dir = settings.data_dir / "provenance"
    g = make_gemini_generate(settings.google_api_key, settings.gemini_model, "LOW")
    m = make_mistral_generate(settings.mistral_api_key, settings.extraction_model)
    for stem in STEMS:
        md = (settings.ocr_dir / f"{stem}.md").read_text(encoding="utf-8")
        gemini = SectionedGeminiExtractor(g).extract(md, stem)
        mistral = SectionedGeminiExtractor(m).extract(md, stem)
        agreement = compute_agreement(gemini, mistral, SECTIONS)
        path = write_provenance(stem, agreement, provenance_dir)
        print(f"{stem}: {agreement} -> {path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it (costs money: 4 CAOs x 12 calls)**

Run: `python3 scripts/backfill_provenance.py`
Expected: 4 lines printed, each with per-section ratios and a written sidecar path. Verify `ls data/provenance/*.provenance.json` shows 4 files (no `test_*`).

- [ ] **Step 3: Spot-check a sidecar**

Run: `cat data/provenance/1049-ikea-cao-1-10-2023-tm-31-12-2024-v07022024.provenance.json`
Expected: `status: unverified`, `source: inter_model_agreement`, `sections` with ratios, `confidence` = their mean.

- [ ] **Step 4: Commit** (script + the 4 sidecars)

```bash
git add scripts/backfill_provenance.py data/provenance/
git commit -m "feat: backfill inter-model-agreement provenance for 4 ground-truth CAOs"
```

---

## Self-Review

- **Spec coverage:** §3 dataflow → Task 1 (Mistral) + Task 5 (wiring); §4 components → Task 1 (make_mistral_generate), Task 2-3 (agreement.py), Task 4 (Provenance.sections + writer); §5 integration (`--provenance` opt-in) → Task 5; §6 error-handling (None for unmeasurable, no sidecar on total failure) → Task 3 (None) + writer (skips) + Task 5 (Mistral failure isolated by SectionedGeminiExtractor); §7 testing → Tasks 2-4 unit + Task 5 online; §8 backfill (4 CAOs) → Task 6. §2 honesty (source=inter_model_agreement, status=unverified) → Task 4 writer.
- **Placeholder scan:** none — full code in every step. The only verify-at-impl note (`settings.provenance_dir` existence) has a concrete fallback instruction.
- **Type consistency:** `make_mistral_generate(api_key, model) -> GenerateFn`; `normalize_value(value) -> str`; `section_agreement(slice_a, slice_b) -> float | None`; `compute_agreement(gemini_doc, mistral_doc, sections) -> dict`; `write_provenance(cao_id, sections_agreement, provenance_dir) -> Path | None`; `Provenance.sections: dict[str,float] | None`. Consistent across tasks.
