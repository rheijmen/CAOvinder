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
