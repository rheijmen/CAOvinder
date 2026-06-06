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
