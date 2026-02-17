"""Statutory References Extraction using Mistral.

Extracts government-mandated parameters:
- WML (Wettelijk Minimumloon) rates
- SV-premies (social insurance premiums)
- Fiscal limits (onbelaste vergoedingen, WKR)
- AOW-leeftijd (state retirement age)
- Pension fund parameters (StiPP franchise, etc.)
- Regulatory changes

These are stored SEPARATELY from SETU data, never merged.
"""

import json
from datetime import datetime
from pathlib import Path

import structlog
from mistralai import Mistral

logger = structlog.get_logger(__name__)

# Load Statutory References schema
STATUTORY_SCHEMA_PATH = Path(__file__).parent.parent / "models" / "statutory_references_schema.json"
STATUTORY_SCHEMA = json.loads(STATUTORY_SCHEMA_PATH.read_text())


STATUTORY_EXTRACTION_PROMPT = """Je bent een expert in Nederlandse arbeidswetgeving en overheidsregulering.

Extraheer ALLEEN de WETTELIJK VERPLICHTE parameters uit dit document. Dit zijn overheidsmaatregelen, NIET wat de inlener biedt.

KRITIEKE ROUTING REGEL - Store separately, compare at read time, NEVER merge:
- Statutory = wat de overheid VERPLICHT (WML, SV-premies, fiscale maxima, AOW-leeftijd)
- SETU = wat de inlener BIEDT (CAO-voorwaarden, loonschalen, toeslagen)
- Extraheer ALLEEN wettelijke parameters. NEGEER CAO-specifieke voorwaarden.

EXTRACT DEZE CATEGORIEËN:

1. minimumWage (WML):
   - Wettelijk minimumuurloon per leeftijdscategorie
   - "WML per 1 januari €14,06", "jeugdloon 18 jaar: €11,25"
   - NIET: CAO-loonschalen of periodieken

2. socialInsurancePremiums (SV-premies):
   - WW-premie (laag/hoog), ZVW, WAO/WIA, Awf, Whk
   - "WW-premie 2026: 2,64%", "ZVW werkgeversbijdrage 6,68%"
   - NIET: Pensioenpremies van de inlener

3. fiscalLimits:
   - Onbelaste reiskostenvergoeding max
   - Thuiswerkvergoeding max
   - WKR vrije ruimte
   - 30%-regeling
   - "Onbelaste km-vergoeding €0,23", "WKR 1,92% van loonsom"
   - NIET: Wat de inlener daadwerkelijk vergoedt

4. stateRetirementAge (AOW-leeftijd):
   - Pensioengerechtigde leeftijd per geboortejaar
   - "AOW-leeftijd 1960: 67 jaar en 3 maanden"
   - NIET: Vervroegd pensioen CAO-regelingen

5. pensionParameters (Pensioenfonds parameters):
   - StiPP franchise bedrag
   - Verplichte pensioenpremies sector
   - "StiPP franchise 2026: €16.000"
   - NIET: Wat de inlener vrijwillig bijdraagt

6. regulatoryChanges (Wetgeving):
   - Wet Gelijkwaardige Beloning
   - WAZO uitbreidingen
   - Wet toekomst pensioenen
   - "WGB ingangsdatum 1-1-2026"

DISAMBIGUATIE:
- "Minimumloon €14,06" → Statutory minimumWage
  "Loonschaal met WML als basis" → NEGEER (is SETU salaryStep.minimumWage flag)
- "Onbelaste reiskosten max €0,23" → Statutory fiscalLimits
  "Werkgever vergoedt €0,23/km" → NEGEER (is SETU allowance)
- "StiPP franchise €16.000" → Statutory pensionParameters
  "Werkgever betaalt 4% pensioen" → NEGEER (is SETU pension)

Als een categorie niet voorkomt in de tekst, laat het veld leeg of null.

Het resultaat MOET een geldig Statutory References v1.0 object zijn volgens het schema.
"""


class MistralStatutoryExtractor:
    """Extract statutory references using Mistral's structured output."""

    def __init__(self, api_key: str, model: str = "mistral-large-latest") -> None:
        self._client = Mistral(api_key=api_key)
        self._model = model

    def extract(
        self,
        markdown: str,
        cao_name: str | None = None,
        beloningsregister_id: str | None = None,
    ) -> dict:
        """Extract statutory references from CAO markdown.

        Args:
            markdown: CAO text from OCR
            cao_name: CAO name for logging
            beloningsregister_id: Optional link to SETU documentId.value

        Returns:
            Statutory references dict matching the schema
        """
        logger.info(
            "Extracting statutory references with Mistral",
            model=self._model,
            cao=cao_name,
            linked_setu=beloningsregister_id,
        )
        start = datetime.utcnow()

        # Truncate to context window
        text = markdown[:500_000]  # Mistral Large 128k token context

        response = self._client.chat.complete(
            model=self._model,
            messages=[
                {"role": "system", "content": STATUTORY_EXTRACTION_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"CAO Naam: {cao_name or 'Onbekend'}\n"
                        f"Beloningsregister ID (optioneel): {beloningsregister_id or 'N/A'}\n\n"
                        f"Statutory References Schema:\n```json\n{json.dumps(STATUTORY_SCHEMA, indent=2)}\n```\n\n"
                        f"CAO Document (Markdown):\n\n{text}"
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.1,  # Low temperature for factual extraction
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        # Add metadata
        if beloningsregister_id:
            data["beloningsregisterId"] = beloningsregister_id

        # Ensure required fields
        if "schemaVersion" not in data:
            data["schemaVersion"] = "1.0.0"

        elapsed = (datetime.utcnow() - start).total_seconds()
        logger.info(
            "Statutory extraction complete",
            model=self._model,
            elapsed_seconds=elapsed,
            has_minimum_wage=bool(data.get("minimumWage")),
            has_sv_premiums=bool(data.get("socialInsurancePremiums")),
            has_fiscal_limits=bool(data.get("fiscalLimits")),
        )

        return data
