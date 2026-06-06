import json

from cao_engine.extraction.sectioned.gemini_sectioned import SectionedGeminiExtractor
from cao_engine.extraction.sectioned.sections import SectionSpec


def _spec(key, keys):
    return SectionSpec(key=key, top_level_keys=keys, prompt_focus=f"focus {key}")


def test_runs_each_section_and_merges_slices():
    sections = [_spec("identity", ["documentId"]), _spec("remuneration", ["remuneration"])]
    returns = {
        "identity": (json.dumps({"documentId": {"value": "X"}}), "STOP"),
        "remuneration": (json.dumps({"remuneration": [{"salaryScale": []}]}), "STOP"),
    }
    calls = []

    def fake_generate(prompt, schema):
        key = "identity" if "focus identity" in prompt else "remuneration"
        calls.append(key)
        return returns[key]

    extractor = SectionedGeminiExtractor(fake_generate, sections=sections)
    result = extractor.extract("MD", "CAO")

    assert calls == ["identity", "remuneration"]
    assert result["documentId"] == {"value": "X"}
    assert result["remuneration"] == [{"salaryScale": []}]
    assert result["_section_meta"]["identity"]["ok"] is True
    assert result["_section_meta"]["remuneration"]["finish"] == "STOP"


def test_failing_section_is_isolated():
    sections = [_spec("identity", ["documentId"]), _spec("remuneration", ["remuneration"])]

    def fake_generate(prompt, schema):
        if "focus remuneration" in prompt:
            raise RuntimeError("API 500")
        return json.dumps({"documentId": {"value": "X"}}), "STOP"

    result = SectionedGeminiExtractor(fake_generate, sections=sections).extract("MD", "CAO")
    assert result["documentId"] == {"value": "X"}          # good section survived
    assert result["_section_meta"]["remuneration"]["ok"] is False
    assert "API 500" in result["_section_meta"]["remuneration"]["error"]


def test_bad_json_is_isolated():
    sections = [_spec("identity", ["documentId"])]

    def fake_generate(prompt, schema):
        return "{not valid json", "STOP"

    result = SectionedGeminiExtractor(fake_generate, sections=sections).extract("MD", "CAO")
    assert result["_section_meta"]["identity"]["ok"] is False
