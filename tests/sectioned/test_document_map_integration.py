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
    full = ocr.full_markdown
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
