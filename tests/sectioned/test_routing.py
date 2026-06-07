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


def test_inline_wage_grid_without_tables_rescues_to_remuneration():
    # Defends against inline-only OCR: page.tables empty, wage grid left in the body.
    # Heading + body have NO anchors, and there are no extracted tables -> the ONLY
    # path to remuneration is the body-scan rescue (>= 6 two-decimal money numbers).
    wage_body = _LONG + "\n" + "\n".join(f"groep {i}: {10 + i},{i:02d}" for i in range(8))
    doc = DocumentMap(sections=[
        _section(0, "Bijlage A overzicht bedragen", body=wage_body, tables=[]),
    ])
    result = route_sections(doc, SECTIONS, fallback_markdown="FALLBACK")
    assert "Bijlage A overzicht bedragen" in result.inputs["remuneration"]


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
