"""Deterministic inter-model agreement: how often two extractions match, per section.

Honest signal, NOT a correctness claim. Normalization absorbs cosmetic differences
(Dutch money formatting, casing, whitespace) so the ratio reflects real disagreement,
not formatting noise.
"""
import re
from collections import Counter

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


def _value_multiset(obj) -> Counter:
    """Multiset of (index-stripped path, normalized value) leaf pairs.

    Array indices are collapsed to `[]` so that the same fact at a different array
    position (or with a different cardinality) still matches — we measure agreement
    on extracted content, not on index alignment.
    """
    counter: Counter = Counter()

    def walk(node, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if not key.startswith("_"):
                    walk(value, f"{path}.{key}" if path else key)
        elif isinstance(node, list):
            for value in node:
                walk(value, f"{path}[]")
        else:
            counter[(path, normalize_value(node))] += 1

    walk(obj, "")
    return counter


def section_agreement(slice_a: dict, slice_b: dict) -> float | None:
    """Multiset Jaccard over (path-template, normalized value) pairs.

    Robust to array order and cardinality; normalization absorbs formatting. Returns
    None when there is nothing to compare on either side.
    """
    a = _value_multiset(slice_a)
    b = _value_multiset(slice_b)
    if not a and not b:
        return None
    intersection = sum((a & b).values())
    union = sum((a | b).values())
    return intersection / union if union else None


def compute_agreement(gemini_doc: dict, mistral_doc: dict, sections) -> dict:
    """Per-section agreement ratio (or None if unmeasurable) keyed by section.key."""
    result = {}
    for spec in sections:
        gemini_slice = {k: gemini_doc[k] for k in spec.top_level_keys if k in gemini_doc}
        mistral_slice = {k: mistral_doc[k] for k in spec.top_level_keys if k in mistral_doc}
        result[spec.key] = section_agreement(gemini_slice, mistral_slice)
    return result
