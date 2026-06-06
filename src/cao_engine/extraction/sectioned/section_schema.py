"""Build a small, Gemini-safe response_schema for a set of top-level SETU keys.

The rc.1 SETU schema is a bundle of named types; the root is InquiryPayEquity and
refs are OpenAPI-style #/components/schemas/X. The Gemini API rejects oneOf,
discriminator, additionalProperties, deep nesting, and unresolved refs. This transform
slices the requested top-level properties, INLINES refs from the bundle, strips the
rejected keywords, and caps depth (which also breaks the recursive Condition type).
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
_MAX_DEPTH = 4


def _resolve(obj, depth):
    if depth >= _MAX_DEPTH:
        if isinstance(obj, dict) and obj.get("type") == "array":
            return {"type": "array", "items": {"type": "object"}}
        return {"type": "object"}
    if isinstance(obj, dict):
        if "$ref" in obj:
            name = obj["$ref"].split("/")[-1]
            target = _DEFS.get(name)
            return _resolve(target, depth + 1) if target is not None else {"type": "object"}
        if any(k in obj for k in _POLY):
            return {"type": "object"}
        out = {}
        for key, value in obj.items():
            if key in _STRIP:
                continue
            out[key] = _resolve(value, depth + 1) if isinstance(value, (dict, list)) else value
        req = out.get("required")
        if isinstance(req, list):
            props = out.get("properties")
            kept = [r for r in req if isinstance(props, dict) and r in props]
            if kept:
                out["required"] = kept
            else:
                out.pop("required", None)
        return out
    if isinstance(obj, list):
        return [_resolve(item, depth) for item in obj]
    return obj


def build_section_schema(top_level_keys: list[str]) -> dict:
    ipe_props = _RC1["InquiryPayEquity"]["properties"]
    props = {k: ipe_props[k] for k in top_level_keys if k in ipe_props}
    return _resolve({"type": "object", "properties": props}, 0)
