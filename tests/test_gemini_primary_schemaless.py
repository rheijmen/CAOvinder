"""Gemini primary extraction is schema-less + post-validated (not response_schema).

The rc.1 SETU schema cannot be a Gemini response_schema: its Condition type uses
oneOf/discriminator, which the google-genai structured-output Schema rejects
(extra_forbidden). The pre-existing code passed an all-None SETU_SCHEMA built by
reading top-level type/properties/$defs from the rc.1 bundle (which has none),
crashing SDK 1.66.0 on $defs. We extract schema-less (rich prose prompt + JSON mime)
and validate against the compliance engine afterwards.
"""
from cao_engine.extraction.gemini_primary import GeminiPrimaryExtractor


def test_extractor_passes_no_response_schema():
    ext = GeminiPrimaryExtractor("dummy-key", "gemini-3.5-flash", "LOW")
    # No (broken) response_schema is handed to the SDK -> no $defs crash.
    assert ext._config.response_schema is None
    # JSON output is still requested via mime type.
    assert ext._config.response_mime_type == "application/json"
