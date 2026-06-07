import copy

from cao_engine.extraction.sectioned.sections import SECTIONS

ALL_18 = {
    "documentId", "versionId", "issued", "effectivePeriod", "customer",
    "baseDefinition", "labourAgreements", "positionProfile", "remuneration",
    "allowance", "holidayAllowance", "sickPay", "leave", "individualChoiceBudget",
    "pension", "sustainableEmployability", "supplementaryArrangement", "otherArrangement",
}


def test_six_sections_cover_all_18_keys_disjointly():
    assert len(SECTIONS) == 6
    seen = []
    for spec in SECTIONS:
        seen.extend(spec.top_level_keys)
    assert sorted(seen) == sorted(ALL_18)          # cover everything
    assert len(seen) == len(set(seen))             # no overlap (disjoint)


def test_each_section_builds_a_gemini_safe_schema():
    from google.genai import _transformers
    for spec in SECTIONS:
        _transformers.t_schema(None, copy.deepcopy(spec.schema))  # must not raise


def test_leave_section_uses_lower_depth_for_live_api():
    """leave/sickPay at depth 8 is rejected by the live API (generic 400); it must
    stay capped at 6. Regression guard for the online-validation finding."""
    leave = next(s for s in SECTIONS if s.key == "leave")
    assert leave.max_depth == 6


def test_build_prompt_includes_focus_and_markdown():
    spec = next(s for s in SECTIONS if s.key == "remuneration")
    prompt = spec.build_prompt("MARKDOWN_BODY", "IKEA CAO")
    assert "MARKDOWN_BODY" in prompt
    assert "IKEA CAO" in prompt
    assert spec.prompt_focus in prompt
