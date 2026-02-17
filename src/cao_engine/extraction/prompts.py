"""LLM prompts for structured CAO data extraction.

All prompts are designed for Dutch CAO documents and instruct the model
to return structured JSON conforming to our Pydantic schemas.
"""

CAO_METADATA_PROMPT = """\
Je bent een expert in Nederlandse Collectieve Arbeidsovereenkomsten (CAO's).

Analyseer het volgende CAO-document en extraheer de metadata. Let op:
- De officiële naam van de CAO
- SBI-codes of sectoraanduiding
- Ingangsdatum en einddatum van de CAO
- Of er een AVV (Algemeen Verbindend Verklaring) van kracht is
- Alle betrokken partijen (werkgevers- en werknemersorganisaties)
- Versienummer of aanduiding

Geef het resultaat als JSON conform het opgegeven schema.
Als een veld niet gevonden kan worden, gebruik null.
"""

LOONGEBOUW_PROMPT = """\
Je bent een expert in Nederlandse CAO-loongebouwen.

Extraheer het complete loongebouw uit dit CAO-document:
- Alle functiegroepen met hun codes en namen
- Salarisschalen per functiegroep
- Treden (stappen) met periodelonen
- Uurlonen indien vermeld
- Leeftijdslonen indien van toepassing
- Het loontijdvak (uur/week/maand/jaar)
- De peildatum van de loontabel

Let specifiek op:
- Tabellen met loonbedragen - extraheer ALLE rijen en kolommen
- Merged cells in tabellen
- Voetnoten bij loontabellen
- Verschillende tabellen voor verschillende periodes

Geef het resultaat als JSON conform het opgegeven schema.
Gebruik Decimal-notatie voor alle bedragen (bijv. "2847.50", niet "2847,50").
"""

ARBEIDSVOORWAARDEN_PROMPT = """\
Je bent een expert in Nederlandse arbeidsvoorwaarden uit CAO's.

Extraheer alle arbeidsvoorwaarden uit dit CAO-document:

1. Vakantietoeslag: percentage, grondslag, uitbetalingsmaand
2. Eindejaarsuitkering: percentage, grondslag, voorwaarden
3. ADV/ATV-regeling: uren per week, ADV-uren/dagen per jaar, compensatie
4. Toeslagen: alle soorten (overwerk, onregelmatig, ploegen, feestdagen, etc.)
   met percentages, bedragen en voorwaarden
5. Onkostenvergoedingen: reiskosten, thuiswerk, maaltijd, etc.
6. Verlof: wettelijk, bovenwettelijk, bijzonder verlof met redenen en dagen
7. Pensioen: regeling, fonds, franchise, premieverdeling
8. Proeftijd en opzegtermijnen

Geef het resultaat als JSON conform het opgegeven schema.
"""

INLENERSBELONING_PROMPT = """\
Je bent een expert in de Nederlandse inlenersbeloning voor uitzendkrachten.

Extraheer alle elementen van de inlenersbeloning uit dit CAO-document:
1. Periodeloon in de schaal
2. ADV/arbeidsduurverkorting
3. Toeslagen (overwerk, onregelmatig, etc.)
4. Initiële loonsverhoging
5. Kostenvergoedingen
6. Periodieken
7. Reisuren/reistijd
8. Eenmalige uitkeringen
9. Thuiswerkvergoeding
10. Vaste eindejaarsuitkering

Per element: geef aan of het van toepassing is, en wat de specifieke regeling is.

Geef het resultaat als JSON conform het opgegeven schema.
"""

MOMENTEN_PROMPT = """\
Je bent een expert in Nederlandse CAO's en het identificeren van alle relevante \
"momenten" - datums, triggers en events die impact hebben op beloning en arbeidsvoorwaarden.

Analyseer dit CAO-document en identificeer ALLE momenten. Een moment is elke \
datum-gedreven trigger, regel of event. Categorieën:

**LOON momenten:**
- Loonsverhogingen (datum + percentage + wie)
- Periodieke verhogingen (treden, per dienstjaar)
- Leeftijdsloon overgangen
- Minimumloon aanpassingen

**DOCUMENT momenten:**
- CAO ingangsdatum en einddatum
- AVV start en eind
- Nawerking periode

**UITKERING momenten:**
- Vakantietoeslag uitbetaling (welke maand)
- Eindejaarsuitkering (wanneer)
- Eenmalige uitkeringen

**WERKNEMER momenten (regels die per werknemer berekend worden):**
- Wanneer volgende periodiek
- Leeftijdsovergangen
- Proeftijd einde
- Contract/fase overgangen

**TOESLAG momenten:**
- Wijzigingen in toeslagpercentages
- Nieuwe of vervallen toeslagen
- Seizoensgebonden regelingen

**PENSIOEN momenten:**
- Premiewijzigingen
- Franchise aanpassingen

Per moment MOET je vastleggen:
1. categorie en type
2. datum (exact of beschrijving zoals "per 1 januari van elk jaar")
3. of het terugkerend is en de frequentie
4. wat er precies verandert (element, oude/nieuwe waarde, percentage, bedrag)
5. wie het betreft (doelgroep, functiegroepen)
6. voorwaarden die gelden
7. het artikel in de CAO (bron_artikel)
8. de EXACTE originele tekst uit de CAO die deze regel beschrijft (bron_tekst)

Wees grondig. Mis geen enkel moment. Geef het resultaat als JSON conform het schema.
"""
