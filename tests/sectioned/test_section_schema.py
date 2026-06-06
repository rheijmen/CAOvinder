import copy

from cao_engine.extraction.sectioned.section_schema import build_section_schema


def test_remuneration_schema_is_gemini_safe_and_inlined():
    schema = build_section_schema(["remuneration"])
    blob = __import__("json").dumps(schema)
    assert schema["type"] == "object"
    assert "remuneration" in schema["properties"]
    for forbidden in ("oneOf", "discriminator", "anyOf", "allOf",
                      "additionalProperties", "$ref", "$defs", "required"):
        assert f'"{forbidden}"' not in blob, forbidden


def test_built_schema_is_accepted_by_genai_sdk():
    from google.genai import _transformers
    schema = build_section_schema(["remuneration", "pension"])
    _transformers.t_schema(None, copy.deepcopy(schema))  # must not raise


def test_unknown_top_level_key_is_ignored():
    schema = build_section_schema(["remuneration", "doesNotExist"])
    assert "doesNotExist" not in schema["properties"]
    assert "remuneration" in schema["properties"]
