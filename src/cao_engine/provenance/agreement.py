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
