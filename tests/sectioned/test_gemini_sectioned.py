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


def test_routed_inputs_feed_each_pass_its_own_slice():
    from cao_engine.extraction.sectioned import SectionedGeminiExtractor
    from cao_engine.extraction.sectioned.sections import SECTIONS

    seen: dict[str, str] = {}

    # capture which markdown each section pass received (prompt embeds the markdown)
    specs = SECTIONS

    def fake_generate(prompt: str, schema: dict) -> tuple[str, str]:
        for spec in specs:
            if spec.prompt_focus[:20] in prompt:
                seen[spec.key] = prompt
        return "{}", "STOP"

    routed = {spec.key: f"SLICE_FOR_{spec.key}" for spec in specs}
    SectionedGeminiExtractor(fake_generate).extract("WHOLE_DOC", "X", routed_inputs=routed)

    assert "SLICE_FOR_remuneration" in seen["remuneration"]
    assert "WHOLE_DOC" not in seen["remuneration"]


def test_without_routed_inputs_uses_whole_markdown():
    from cao_engine.extraction.sectioned import SectionedGeminiExtractor

    prompts: list[str] = []

    def fake_generate(prompt: str, schema: dict) -> tuple[str, str]:
        prompts.append(prompt)
        return "{}", "STOP"

    SectionedGeminiExtractor(fake_generate).extract("WHOLE_DOC", "X")
    assert all("WHOLE_DOC" in p for p in prompts)
