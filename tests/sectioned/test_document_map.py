"""Unit tests for build_document_map (pure, no network)."""
from cao_engine.extraction.sectioned.document_map import (
    DocumentMap,
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
