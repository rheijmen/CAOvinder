"""Online validation: sectioned extraction against ground-truth anchors (ikea).

Marked `online` (skipped by default; needs GOOGLE_API_KEY and costs money). This is
the gate that confirms ALL 6 bundles work end-to-end, not just remuneration.
Anchors are facts verified by hand from the ikea OCR — NOT leaf-count vs another model.
"""
import json
import os
from pathlib import Path

import pytest

try:
    from dotenv import load_dotenv

    load_dotenv()  # make GOOGLE_API_KEY from .env available to this online test
except ImportError:
    pass

from cao_engine.extraction.sectioned import SectionedGeminiExtractor, make_gemini_generate

pytestmark = pytest.mark.online

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OCR = _REPO_ROOT / "data" / "ocr" / "1049-ikea-cao-1-10-2023-tm-31-12-2024-v07022024.md"


@pytest.mark.skipif(not os.environ.get("GOOGLE_API_KEY"), reason="no GOOGLE_API_KEY")
def test_ikea_sectioned_extraction_hits_ground_truth_anchors():
    markdown = OCR.read_text(encoding="utf-8")
    generate = make_gemini_generate(os.environ["GOOGLE_API_KEY"], "gemini-3.5-flash", "LOW")
    doc = SectionedGeminiExtractor(generate).extract(markdown, "IKEA CAO 2023-2024")

    # every section completed
    assert all(m["ok"] for m in doc["_section_meta"].values()), doc["_section_meta"]

    # ground-truth anchors pulled from the ikea OCR
    assert "ikea" in json.dumps(doc.get("customer", {}), ensure_ascii=False).lower()
    assert "2023-10-01" in json.dumps(doc.get("effectivePeriod", {}))
    assert "2024-12-31" in json.dumps(doc.get("effectivePeriod", {}))
    assert doc.get("holidayAllowance"), "vakantietoeslag missing"
    assert doc.get("pension"), "pension missing"

    # richness: many salary steps (spike got 126)
    steps = [
        s
        for pkg in doc.get("remuneration", [])
        for sc in pkg.get("salaryScale", [])
        for s in sc.get("salaryStep", [])
    ]
    assert len(steps) >= 20, f"only {len(steps)} salary steps"


@pytest.mark.skipif(
    not os.environ.get("GOOGLE_API_KEY") or not os.environ.get("MISTRAL_API_KEY"),
    reason="needs GOOGLE_API_KEY and MISTRAL_API_KEY",
)
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
    print("INTER-MODEL AGREEMENT:", agreement)
    measured = {k: v for k, v in agreement.items() if v is not None}
    assert measured, "no section was measurable"
    assert all(0.0 <= v <= 1.0 for v in measured.values()), agreement
    # metric is non-degenerate: at least one section shows real agreement.
    # Robust low bar: honest inter-model agreement is genuinely LOW (observed per-CAO
    # maxes 0.20-0.27 across the 4 ground-truth CAOs) and varies per LLM run; metric
    # correctness itself is unit-tested in tests/provenance/test_agreement.py.
    assert max(measured.values()) > 0.1, agreement

