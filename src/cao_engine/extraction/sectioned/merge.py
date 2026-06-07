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
