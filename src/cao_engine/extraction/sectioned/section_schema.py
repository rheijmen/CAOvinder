"""Build a small, Gemini-safe response_schema for a set of top-level SETU keys.

The rc.1 SETU schema is a bundle of named types; the root is InquiryPayEquity and
refs are OpenAPI-style #/components/schemas/X. The Gemini API rejects oneOf,
discriminator, additionalProperties, `required` mismatches, and unresolved refs, and
chokes on very deep nesting. This transform slices the requested top-level properties,
INLINES refs, strips the rejected keywords, and caps nesting at object/array *type
boundaries* (not at every dict level — that would collapse a section to empty objects).
Recursion (the polymorphic Condition type) is handled by the polymorphism strip, not by
the depth cap, so the cap can stay generous and preserve real structure (e.g. the
salaryScale -> salaryStep nesting that drives rich extraction).
"""
import json
from pathlib import Path

_SCHEMA_PATH = (
    Path(__file__).parent.parent.parent / "compliance" / "schemas" / "setu_v2.0.0-rc.1.json"
)
_RC1 = json.loads(_SCHEMA_PATH.read_text())
_DEFS = dict(_RC1)  # all 89 named types resolve by name

_STRIP = ("$schema", "$id", "title", "description", "additionalProperties")
_POLY = ("oneOf", "anyOf", "allOf", "discriminator")
_DEFAULT_MAX_DEPTH = 8


def _resolve(node: dict, depth: int, max_depth: int) -> dict:
    if not isinstance(node, dict):
        return node
    if "$ref" in node:  # inline a referenced type at the SAME depth (a ref is not a level)
        target = _DEFS.get(node["$ref"].split("/")[-1])
        return _resolve(target, depth, max_depth) if target is not None else {"type": "object"}
    if any(k in node for k in _POLY):  # polymorphic/recursive -> permissive object
        return {"type": "object"}
    node = {k: v for k, v in node.items() if k not in _STRIP}
    node_type = node.get("type")
    if node_type == "object" and "properties" in node:
        if depth >= max_depth:
            return {"type": "object"}
        props = {k: _resolve(v, depth + 1, max_depth) for k, v in node["properties"].items()}
        return {"type": "object", "properties": props}
    if node_type == "array" and "items" in node:
        if depth >= max_depth:
            return {"type": "array", "items": {"type": "object"}}
        return {"type": "array", "items": _resolve(node["items"], depth + 1, max_depth)}
    return node  # scalar / leaf schema (drop nothing else)


def build_section_schema(top_level_keys: list[str], max_depth: int = _DEFAULT_MAX_DEPTH) -> dict:
    """Build a Gemini-safe schema. `max_depth` is per-section: deep bundles (e.g. leave)
    must use a lower cap (~6) or the live API rejects them with a generic 400, while the
    salary bundle needs >=7 to preserve the salaryScale->salaryStep nesting."""
    ipe_props = _RC1["InquiryPayEquity"]["properties"]
    props = {k: ipe_props[k] for k in top_level_keys if k in ipe_props}
    return _resolve({"type": "object", "properties": props}, 0, max_depth)
