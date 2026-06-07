# CAO Centraal — Fase C: provenance uit inter-model agreement (design)

> **Status:** design ter review (2026-06-07). Onderdeel van [Masterplan Fase C](2026-06-03-cao-centraal-master-pipeline.md). Bouwt voort op Fase E (PR #2). Volgende stap na akkoord: `superpowers:writing-plans`.

## 1. Probleem & aanleiding

Het product belooft **correctheid-labeling** als aansprakelijkheidsschild, maar levert nu voor alle CAO's alleen de neutrale default `unverified` (geen confidence). De eerdere provenance-poging was geblokkeerd:

- De judge-`agreements`-stats waren prompt-echo (verzonnen, 127/98) — verwijderd in PR #2.
- Deterministische inter-model agreement was onmeetbaar: 3/4 ruwe Gemini-outputs waren degeneraat (single-pass faalde), en zelfs achmea's twee outputs divergeerden structureel (1,1% leaf-agreement) omdat de modellen verschillende sleutels/coderingen gebruikten.

**Fase E deblokkeert dit:** met sectie-gewijze extractie + per-sectie schemas produceren beide modellen nu **dezelfde structuur** → veld-voor-veld vergelijking wordt zinvol.

## 2. Waarheidsstandaard (beslist)

Het signaal meet **inter-model agreement** — consistentie tussen twee onafhankelijke extracties — en wordt **eerlijk als zodanig gelabeld**, NIET als "correct". `status` blijft `unverified`; `source` = `inter_model_agreement`. Een hoge ratio = "twee modellen onafhankelijk eens"; een lage ratio = "nakijken". Geen verzonnen getallen. (Bron-validatie is een sterkere, aparte waarheidsstandaard — buiten scope.)

## 3. Doelarchitectuur

```
Gemini-sectioned  ─┐
                   ├─► compute_agreement(per sectie, genormaliseerd) ─► provenance-sidecar
Mistral-sectioned ─┘   (2 ONAFHANKELIJKE extracties, zelfde 6 sectie-schemas)  data/provenance/{cao_id}.provenance.json
```

- **Gemini-sectioned** (Fase E) blijft de **canonieke** SETU-output.
- **Mistral-sectioned** is een onafhankelijke tweede extractie (ziet Gemini's output NIET), puur als agreement-referentie.
- De `ProvenanceStore` (read-side, uit plan 1a-api) leest de sidecar al at-read-time.

## 4. Componenten (geïsoleerd, elk één doel)

Uitbreiding van het Fase E-pakket `src/cao_engine/extraction/sectioned/` + de serving-laag:

- **`make_mistral_generate(api_key, model)`** in `gemini_sectioned.py` (of een nieuw `mistral_sectioned.py`) — een Mistral-backed `generate(prompt, schema) -> (text, finish)` die de bestaande `SectionedGeminiExtractor` via DI hergebruikt (die is model-agnostisch). ⚠️ **Feasibility-onbekende:** ondersteunt Mistral structured output met onze per-sectie schemas, en levert het vergelijkbare structuur? → **spike als taak 1** (offline-aannames misleidden eerder).
- **`agreement.py`** (nieuw, puur):
  - `normalize_value(v) -> str` — NL-bedragen (`1.500,00` ≡ `1500`), casing/whitespace, datums, booleans, None.
  - `section_agreement(gemini_slice, mistral_slice) -> float` — flatten beide naar leaf-paden, normaliseer, `matched / total` over de unie.
  - `compute_agreement(gemini_doc, mistral_doc, sections) -> dict[str, float]` — per sectie-key een ratio.
- **`provenance.py`** (uitbreiden) — `Provenance` krijgt optioneel veld `sections: dict[str, float] | None = None`; `confidence` = overall (gemiddelde van de sectie-ratios). Backward-compatible (bestaande sidecars zonder `sections` blijven geldig).
- **`provenance_writer.py`** (nieuw) — `write_provenance(cao_id, sections_agreement, provenance_dir)`: schrijft `{cao_id}.provenance.json`; filtert test-artefacten (geen `test_*`).

## 5. Pijplijn-integratie

In `extract_setu_pipeline` via een **opt-in `--provenance` flag** (vereist `--sectioned`; opt-in omdat het de extractie-kosten verdubbelt): na de canonieke Gemini-sectioned extractie ook Mistral-sectioned draaien → `compute_agreement` → `write_provenance`. De Mistral-reviewer en judge blijven voorlopig ongemoeid (een latere stap kan de judge met écht agreement voeden i.p.v. de gekilde nep-stats).

## 6. Error-handling

- Mistral-sectioned hergebruikt de Fase E failure-isolatie: een gefaalde sectie levert een lege slice + vlag; agreement voor die sectie = `None` (niet 0.0 — "niet te meten" ≠ "0% eens"), overgeslagen in de overall.
- Als Mistral-sectioned volledig faalt → geen sidecar schrijven (de read-side valt terug op neutraal `unverified`). Eerlijk.

## 7. Testen (TDD)

- **Spike-first (taak 1):** Mistral-sectioned op ikea → produceert het vergelijkbare structuur per sectie? Bevestig vóór de rest.
- **`agreement.py`:** unit-tests — identieke slices → 1.0; disjuncte → 0.0; NL-getal-normalisatie (`1.500,00`≡`1500`); case-insensitive; array-volgorde-robuustheid; lege slice → `None`.
- **`provenance.py` / writer:** Provenance met `sections` round-trip; writer filtert test-artefacten; overall = gemiddelde.
- **Online (marker `online`):** Gemini- vs Mistral-sectioned op ikea → echte per-sectie ratios; sanity (ratios in [0,1], salaris-sectie ≥ een redelijke drempel gezien de spike's 126 treden).

## 8. Backfill

Bereken provenance voor CAO's waar beide sectioned-extracties bestaan. Initieel een steekproef (de 4 grond-waarheid-CAO's: achmea/groothandel/ikea/rabobank) door beide modellen sectioned te draaien. Volledige 700+ dekking = batch-spoor (Fase G).

## 9. Scope & non-goals

**In scope:** onafhankelijke Mistral-sectioned extractie, agreement-engine, provenance-model-uitbreiding + writer, pijplijn-integratie, backfill-steekproef.

**Niet in scope:** bron-validatie (andere waarheidsstandaard), per-veld granulariteit (nu per-sectie), judge/reviewer-herontwerp, volledige 700+ backfill (Fase G), API-exposure van de per-sectie scores (read-side toont al `confidence`; per-sectie API-veld is een latere, kleine toevoeging).

## 10. Kosten & open risico's

- **Kosten:** +6 Mistral-sectie-passes per CAO (≈ verdubbelt de extractie-kosten). Mistral-prijzen verifiëren; backfill beperkt tot steekproef.
- **Linchpin-risico:** Mistral-structured-output-feasibility met de sectie-schemas. Gemini's schemas gebruiken een Gemini-veilige subset; Mistral's `response_format`/`json_schema` is anders. Mogelijk moeten de schemas licht aangepast of moet Mistral in JSON-mode met alleen de prompts draaien (structuur uit de prompt) — de agreement-normalisatie moet daar robuust tegen zijn. **Spike taak 1 beslist dit vóór de bouw.**
- **Normalisatie-risico:** als de normalisatie te los is, wordt agreement kunstmatig hoog (vals vertrouwen); te streng → kunstmatig laag. Unit-tests met echte CAO-waarden ijken dit.
