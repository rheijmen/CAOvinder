from cao_engine.provenance.agreement import (
    compute_agreement,
    normalize_value,
    section_agreement,
)


def test_dutch_money_normalizes_to_plain_number():
    assert normalize_value("€ 1.500,00") == normalize_value("1500") == normalize_value(1500.0)


def test_decimal_comma_normalizes():
    assert normalize_value("14,25") == normalize_value(14.25)


def test_strings_are_case_and_space_insensitive():
    assert normalize_value("  Functiegroep A ") == normalize_value("functiegroep a")


def test_none_and_bool():
    assert normalize_value(None) == "∅"
    assert normalize_value(True) == "true"


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
