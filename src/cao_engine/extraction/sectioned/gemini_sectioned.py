"""Sectioned Gemini extraction: one focused pass per bundle, then merge.

`generate` is injected (DI) so the orchestration is testable without the SDK:
    generate(prompt: str, schema: dict) -> tuple[json_text: str, finish_reason: str]
"""
import json
from collections.abc import Callable

import structlog

from cao_engine.extraction.sectioned.merge import merge_sections
from cao_engine.extraction.sectioned.sections import SECTIONS, SectionSpec

logger = structlog.get_logger(__name__)

GenerateFn = Callable[[str, dict], tuple[str, str]]


class SectionedGeminiExtractor:
    def __init__(self, generate: GenerateFn, sections: list[SectionSpec] | None = None) -> None:
        self._generate = generate
        self._sections = sections if sections is not None else SECTIONS

    def extract(
        self,
        markdown: str,
        cao_name: str | None = None,
        routed_inputs: dict[str, str] | None = None,
    ) -> dict:
        slices: list[dict] = []
        meta: dict = {}
        for spec in self._sections:
            section_md = (
                routed_inputs[spec.key]
                if routed_inputs and spec.key in routed_inputs
                else markdown
            )
            finish: str | None = None
            try:
                text, finish = self._generate(spec.build_prompt(section_md, cao_name), spec.schema)
                data = json.loads(text)
                slices.append(data)
                meta[spec.key] = {"ok": True, "finish": finish}
                logger.info("section extracted", section=spec.key, finish=finish)
            except Exception as exc:  # API error, JSON parse (truncation), etc. -> isolate
                # keep `finish` so a MAX_TOKENS truncation is distinguishable from an API error
                meta[spec.key] = {"ok": False, "finish": finish, "error": str(exc)}
                logger.warning("section failed", section=spec.key, finish=finish, error=str(exc))
        merged = merge_sections(slices)
        merged["_extraction_metadata"] = {
            "extractor": "gemini-sectioned",
            "cao_name": cao_name,
            "routed": routed_inputs is not None,
            "sections_ok": [k for k, m in meta.items() if m["ok"]],
            "sections_failed": [k for k, m in meta.items() if not m["ok"]],
        }
        merged["_section_meta"] = meta
        return merged


def make_gemini_generate(api_key: str, model: str, thinking_level: str = "LOW") -> GenerateFn:
    """Real generate fn backed by google-genai (schema-constrained, capped output)."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    level = getattr(types.ThinkingLevel, thinking_level.upper(), types.ThinkingLevel.LOW)

    def generate(prompt: str, schema: dict) -> tuple[str, str]:
        config = types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=schema,
            max_output_tokens=65536,
            thinking_config=types.ThinkingConfig(thinking_level=level, include_thoughts=False),
        )
        response = client.models.generate_content(model=model, contents=prompt, config=config)
        finish = str(response.candidates[0].finish_reason)
        return response.text or "", finish

    return generate
