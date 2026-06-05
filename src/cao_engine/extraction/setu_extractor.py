"""SETU v2.0 Structured Data Extraction using Mistral, Claude, and Gemini.

This module implements multi-LLM orchestrated extraction:
1. Three frontier LLMs extract SETU v2.0 JSON in parallel
2. Orchestrator validates and merges outputs
3. Returns high-confidence SETU-compliant data
"""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import structlog
from mistralai import Mistral

logger = structlog.get_logger(__name__)

# Load SETU v2.0 schema
SETU_SCHEMA_PATH = Path(__file__).parent.parent / "models" / "setu_v2_schema.json"
SETU_SCHEMA = json.loads(SETU_SCHEMA_PATH.read_text())


SETU_EXTRACTION_PROMPT = """Je bent een expert in Nederlandse CAO's en SETU v2.0 standaarden.

Extraheer ALLEEN de arbeidsvoorwaarden DIE DE INLENER BIEDT uit deze CAO en structureer het volgens het SETU Inquiry Pay Equity v2.0 schema.

KRITIEKE ROUTING REGEL - Store separately, compare at read time, NEVER merge:
- SETU = wat de inlener BIEDT (CAO-voorwaarden, loonschalen, toeslagen, verlofdagen)
- Statutory = wat de overheid VERPLICHT (WML, SV-premies, fiscale maxima, AOW-leeftijd)
- Extraheer ALLEEN wat de inlener biedt. NEGEER wettelijke minimumlonen, SV-premies, fiscale vrijstellingen.

DISAMBIGUATIE REGELS:
1. "Pensioenregeling met 4% werkgeversbijdrage" → SETU pension
   "StiPP basis premie 12%" → NEGEER (statutory)
2. "Reiskostenvergoeding €0,23/km" → SETU allowance
   "Onbelaste reiskosten max €0,23" → NEGEER (statutory fiscal limit)
3. Loonschaal met "minimumloon" flag → salaryStep.minimumWage = true
   Het WML bedrag zelf → NEGEER (statutory minimumWage)
4. "CAO-verhoging 3% per 1-7-2026" → SETU generalSalaryIncrease
   "WML stijgt naar €14,06" → NEGEER (statutory)
5. "Generatiepact" / "80-90-100" → supplementaryArrangement (NIET otherArrangement)
6. "ADV" / "ATV" / "roostervrije dagen" → leave.adv (NIET paidLeave)
7. "Feestdagen" → leave.holidays (NIET leave.paidLeave)

EXTRACT VOLLEDIG:
- ALLE functiegroepen, schalen, treden, bedragen uit loontabellen
- ALLE toeslagen (ORT, ploegentoeslag, overwerktoeslag, reiskostenvergoeding, etc.)
- Vakantietoeslag percentage en uitbetalingsmoment
- ADV-dagen, feestdagen, bijzonder verlof (in juiste leave subcategories)
- Pensioenregelingen zoals de inlener ze biedt
- IKB, duurzame inzetbaarheid, generatiepact
- Gebruik EXACTE terminologie uit de CAO
- Als een veld onbekend is: null (niet lege string)

Het resultaat MOET een geldig SETU v2.0 InquiryPayEquity object zijn.
"""


class MistralSETUExtractor:
    """Extract SETU v2.0 data using Mistral's structured output."""

    def __init__(self, api_key: str, model: str = "mistral-large-latest") -> None:
        self._client = Mistral(api_key=api_key)
        self._model = model

    def extract(self, markdown: str, cao_name: str | None = None) -> dict:
        """Extract SETU v2.0 structured data from CAO markdown.

        Uses Mistral's Custom Structured Outputs with JSON Schema.
        Returns raw dict (validation happens in orchestrator).
        """
        logger.info("Extracting SETU v2.0 with Mistral", model=self._model, cao=cao_name)
        start = datetime.utcnow()

        # Truncate to context window
        text = markdown[:500_000]  # Mistral Large 128k token context

        response = self._client.chat.complete(
            model=self._model,
            messages=[
                {"role": "system", "content": SETU_EXTRACTION_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"CAO Naam: {cao_name or 'Onbekend'}\n\n"
                        f"SETU v2.0 Schema:\n```json\n{json.dumps(SETU_SCHEMA, indent=2)}\n```\n\n"
                        f"CAO Document (Markdown):\n\n{text}"
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.1,  # Low temperature for factual extraction
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        elapsed = (datetime.utcnow() - start).total_seconds()
        logger.info(
            "Mistral extraction complete",
            model=self._model,
            elapsed_seconds=elapsed,
            has_remuneration=bool(data.get("remuneration")),
            has_allowances=bool(data.get("allowance")),
        )

        return data


# Placeholder classes for Claude and Gemini (to be implemented)
class ClaudeSETUExtractor:
    """Extract SETU v2.0 data using Claude Opus 4.6."""

    def __init__(self, api_key: str, model: str = "claude-opus-4.6-20260205") -> None:
        logger.warning("Claude Opus 4.6 extractor not yet implemented")
        self._model = model

    def extract(self, markdown: str, cao_name: str | None = None) -> dict:
        """Extract SETU v2.0 (PLACEHOLDER - returns empty structure)."""
        logger.info("Claude extraction (placeholder)", model=self._model)
        return {"documentId": {"value": "PLACEHOLDER", "schemeAgencyId": "Claude"}}


class GeminiSETUExtractor:
    """Extract SETU v2.0 data using Gemini 3 Pro."""

    def __init__(self, api_key: str, model: str = "gemini-3-pro-preview") -> None:
        logger.warning("Gemini 3 Pro extractor not yet implemented")
        self._model = model

    def extract(self, markdown: str, cao_name: str | None = None) -> dict:
        """Extract SETU v2.0 (PLACEHOLDER - returns empty structure)."""
        logger.info("Gemini extraction (placeholder)", model=self._model)
        return {"documentId": {"value": "PLACEHOLDER", "schemeAgencyId": "Gemini"}}


class MultiLLMSETUExtractor:
    """Orchestrate extraction across Mistral, Claude, and Gemini in parallel."""

    def __init__(
        self,
        mistral_api_key: str,
        claude_api_key: str | None = None,
        gemini_api_key: str | None = None,
    ) -> None:
        self.mistral = MistralSETUExtractor(mistral_api_key)
        self.claude = ClaudeSETUExtractor(claude_api_key) if claude_api_key else None
        self.gemini = GeminiSETUExtractor(gemini_api_key) if gemini_api_key else None

    def extract_parallel(
        self, markdown: str, cao_name: str | None = None
    ) -> tuple[dict, dict | None, dict | None]:
        """Run all available LLMs in parallel.

        Returns (mistral_output, claude_output, gemini_output).
        None if API key not configured.
        """
        logger.info("Starting multi-LLM parallel extraction", cao=cao_name)
        start = datetime.utcnow()

        extractors = [("mistral", self.mistral)]
        if self.claude:
            extractors.append(("claude", self.claude))
        if self.gemini:
            extractors.append(("gemini", self.gemini))

        with ThreadPoolExecutor(max_workers=len(extractors)) as executor:
            futures = {
                name: executor.submit(extractor.extract, markdown, cao_name)
                for name, extractor in extractors
            }

            results = {name: future.result() for name, future in futures.items()}

        elapsed = (datetime.utcnow() - start).total_seconds()
        logger.info(
            "Parallel extraction complete",
            elapsed_seconds=elapsed,
            models=list(results.keys()),
        )

        return (
            results.get("mistral", {}),
            results.get("claude"),
            results.get("gemini"),
        )

    def extract_with_consensus(self, markdown: str, cao_name: str | None = None) -> dict:
        """Extract with multi-LLM consensus (orchestrator TBD).

        For now, returns Mistral output only.
        TODO: Implement consensus orchestrator.
        """
        mistral_output, claude_output, gemini_output = self.extract_parallel(markdown, cao_name)

        # PLACEHOLDER: Return Mistral for now
        # TODO: Implement orchestrator that compares outputs and achieves consensus
        logger.warning("Consensus orchestrator not yet implemented - returning Mistral output only")

        return mistral_output
