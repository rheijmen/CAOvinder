"""Judge reports must not carry fabricated census stats (the 127/98 prompt-echo).

Root cause: the judge prompt contains an example with total_fields_compared=127,
agreements=98 and the Mistral judge echoes those literals (identical on 3 docs).
Honest fix: aggregate counts are computed in code from the real decisions[], or
omitted entirely. Never LLM-self-reported.
See memory: cao-centraal-judge-report-suspect / cao-centraal-raw-outputs-stale-fase-c.
"""
from cao_engine.extraction.mistral_judge import sanitize_judge_report


def test_drops_fabricated_census_and_recomputes_counts_from_decisions():
    raw = {
        "total_fields_compared": 127,  # prompt-echo, not a real field census
        "agreements": 98,              # prompt-echo
        "gemini_preferred": 21,        # LLM self-report — must be ignored
        "mistral_preferred": 8,
        "merged": 0,
        "decisions": [
            {"field": "documentId", "decision": "mistral"},
            {"field": "a", "decision": "gemini"},
            {"field": "b", "decision": "gemini"},
            {"field": "c", "decision": "merge"},
        ],
    }
    out = sanitize_judge_report(raw)

    # fabricated census numbers gone (we cannot honestly produce them)
    assert "total_fields_compared" not in out
    assert "agreements" not in out

    # honest counts computed from the real decisions[], not the LLM's numbers
    assert out["num_decisions"] == 4
    assert out["gemini_preferred"] == 2
    assert out["mistral_preferred"] == 1
    assert out["merged"] == 1

    # the real decisions are preserved verbatim
    assert out["decisions"] == raw["decisions"]


def test_handles_missing_or_empty_decisions():
    out = sanitize_judge_report({"total_fields_compared": 127, "agreements": 98})

    assert "total_fields_compared" not in out
    assert "agreements" not in out
    assert out["num_decisions"] == 0
    assert out["gemini_preferred"] == 0
    assert out["mistral_preferred"] == 0
    assert out["merged"] == 0
    assert out["decisions"] == []
