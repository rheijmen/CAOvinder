"""Independent Mistral sectioned extraction for inter-model agreement (Fase C).

Mistral runs the SAME 6 section passes as Gemini, with the SAME section schemas
(spike-confirmed: Mistral accepts them via strict json_schema). It does NOT see
Gemini's output -> the two extractions are independent. Provides a `generate`
callable for the model-agnostic SectionedGeminiExtractor.
"""
from collections.abc import Callable

GenerateFn = Callable[[str, dict], tuple[str, str]]


def make_mistral_generate(api_key: str, model: str = "mistral-large-latest") -> GenerateFn:
    from mistralai import Mistral

    client = Mistral(api_key=api_key)

    def generate(prompt: str, schema: dict) -> tuple[str, str]:
        response = client.chat.complete(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "section", "schema": schema, "strict": True},
            },
            temperature=0.1,
        )
        choice = response.choices[0]
        return choice.message.content or "", str(choice.finish_reason)

    return generate
