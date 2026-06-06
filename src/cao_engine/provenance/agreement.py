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
