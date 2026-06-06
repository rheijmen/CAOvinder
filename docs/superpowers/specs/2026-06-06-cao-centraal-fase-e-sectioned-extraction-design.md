# CAO Centraal — Fase E: sectie-gewijze Gemini-extractie (design)

> **Status:** design ter review (2026-06-06). Onderdeel van [Masterplan Fase E](2026-06-03-cao-centraal-master-pipeline.md). Volgende stap na akkoord: `superpowers:writing-plans` → TDD-implementatie.

## 1. Probleem & aanleiding

Single-pass Gemini-extractie van een complete CAO naar SETU v2.0 **kan niet winnen** (empirisch vastgesteld, 2026-06-05/06):

- **Schema-loos** (huidige werkende staat, commit `9ec9c69`): het model stopt vrijwillig dun — ikea 145 / achmea 124 leaves, `finish=STOP`, terwijl Mistral op ikea 630 leaves haalde. De extractie is onvolledig (mist secties, ondiepe inhoud).
- **Volledig schema afdwingen** kan niet: de rc.1 SETU-schema wordt door de Gemini-API geweigerd (`oneOf`/`discriminator`/`additionalProperties` + nesting-diepte), en zou op grote docs het **65K output-token-plafond** raken (de maart-truncatie van 161KB).

**Kernconclusie:** completeness is geen schema-probleem maar een single-pass-probleem.

## 2. Bewezen hypothese (de-risk-spike)

Een **klein, zelf-bevattend per-sectie `response_schema`** lost het op. Spike (2026-06-06, ikea, gemini-3.5-flash, LOW thinking) op alléén de salaris-sectie:

- **API accepteert** het kleine schema (de afwijzingen golden voor het volledige 91-type schema, niet voor een kleine subset).
- **Rijk**: 26 salaryScales, **126 salarySteps** met echte namen (IPE-Level 43–50) en bedragen (Zone 1 Min 14.08…).
- **Past in budget**: output 5525 tokens, `finish=STOP`.

Eén sectie-pass leverde meer rijke salaris-data dan de hele-doc schema-loze extractie (~145 leaves totaal). Het fundament is daarmee gede-riskt.

## 3. Doelarchitectuur

```
SectionedGeminiExtractor.extract(markdown, cao_name) → één complete SETU-dict
   voor elk van 6 secties:
      slice = GeminiSectionPass(section.schema, section.prompt).run(markdown, cao_name)   # 1 API-call
   merged = merge_sections(slices)        # deterministische assemblage
   compliance_engine.validate(merged)     # kwaliteitspoort (niet-blokkerend; rapport opslaan)
   → merged
```

**Integratie:** vervangt **Step 1** (`gemini.extract(...)`) in `extract_setu_pipeline` (cli.py). De bestaande Mistral-reviewer en judge consumeren de nu-complete Gemini-output **ongewijzigd**. Provenance/confidence (Fase C) blijft een apart, later spoor.

## 4. De 6 bundels (disjuncte top-level keys)

Elke bundel bezit een **disjuncte** set van de 18 InquiryPayEquity top-level properties. Daardoor is de merge een simpele key-union zonder conflict-resolutie.

| # | Bundel | Top-level keys |
|---|--------|----------------|
| 1 | Identiteit | `documentId`, `versionId`, `issued`, `effectivePeriod`, `customer`, `labourAgreements`, `positionProfile`, `baseDefinition` |
| 2 | Remuneration | `remuneration` (salaryScale + salaryStep + general/individualSalaryIncrease) — *bewezen zwaar* |
| 3 | Toeslagen | `allowance`, `holidayAllowance` |
| 4 | Verlof | `leave`, `sickPay` |
| 5 | Pensioen/IKB | `pension`, `individualChoiceBudget`, `sustainableEmployability` |
| 6 | Aanvullend | `supplementaryArrangement`, `otherArrangement` |

## 5. Componenten (geïsoleerd, elk één doel)

Nieuw pakket `src/cao_engine/extraction/sectioned/`:

- **`sections.py`** — 6 `SectionSpec`s, pure data: `key`, de top-level keys die de bundel bezit, het kleine self-contained `response_schema`, en een gefocuste prompt-fragment. Geen logica.
- **`section_schema.py`** — `build_section_schema(component_types)`: kleine transform die uit de rc.1-componenttypes een Gemini-veilig schema bouwt (strip `oneOf`/`discriminator`/`additionalProperties`/`required`, inline refs, diepte-cap). Houdt de officiële SETU-schema als bron-van-waarheid i.p.v. 6× handmatig schema's onderhouden. Pure functie.
- **`gemini_sectioned.py`** — `GeminiSectionPass` (bouwt config met sectie-schema, doet 1 API-call, parse + `finish_reason`-afhandeling → slice) en `SectionedGeminiExtractor` (orkestreert de 6 passes, isoleert falen, merge + validatie).
- **`merge.py`** — pure `merge_sections(slices) → dict`: key-union van de disjuncte slices tot één InquiryPayEquity-dict; lege/gefaalde slices worden overgeslagen.

## 6. Error-handling & failure-isolatie

- Eén sectie die faalt (API-error, JSON-parse-fout, `finish=MAX_TOKENS`) → die slice is leeg en **gevlagd in metadata**; de andere 5 secties mergen gewoon door. Eén kapotte sectie stopt de CAO-extractie niet.
- `finish=MAX_TOKENS` op een sectie = signaal dat die bundel verder gesplitst moet worden (buiten scope nu; gelogd als waarschuwing).
- Per-sectie structlog-logging (sectie-key, tokens, finish_reason, geslaagd/gefaald).

## 7. Testen (TDD)

- **Per sectie:** (a) offline `t_schema`-acceptatie van het gebouwde schema; (b) online anker-smoke tegen grondwaarheid uit de OCR (bv. remuneration ≥20 salarytreden met bedragen, zoals de spike's 126). Ankers = handmatig geverifieerde feiten uit de bron, **niet** leaf-count vs een ander model (dat is een proxy zonder grondwaarheid).
- **`merge_sections`:** unit-tests — disjuncte keys assembleren correct; lege/gefaalde slices overgeslagen; geen key-collisions.
- **`build_section_schema`:** unit-tests — output is `t_schema`-acceptabel, bevat geen `oneOf`/`additionalProperties`/`required`, refs ge-inlined.
- **Implementatie-taak 1 valideert álle 6 bundels** (offline + smoke). Alleen remuneration is nu empirisch bewezen.

## 8. Scope & non-goals

**In scope:** sectioned-Gemini extractor + merge + compliance-validatie; integratie als Step 1 van `extract_setu_pipeline`.

**Niet in scope (aparte sporen):**
- Provenance/confidence uit inter-model agreement (Fase C — blijft geblokkeerd tot beide modellen vergelijkbaar compleet zijn; sectioned Mistral is een latere optie).
- Mistral-reviewer en judge wijzigen (blijven ongemoeid).
- Sub-sectie-splitsing voor CAO's die per sectie het 65K-plafond raken (alleen gevlagd, niet opgelost).
- Batch-orkestratie over alle 700+ CAO's (Fase G).

## 9. Kosten

Gemeten per sectie-pass (ikea): ~49K input-tok + ~5K output-tok. ⇒ ~6 passes ≈ ~300K input + ~30K output per CAO. Op gemini-3.5-flash-prijzen ruwweg **~$0,03–0,05/CAO** → ~$35–70 voor 700 CAO's (ruwe schatting, prijzen te verifiëren). De cost-gate uit het masterplan lijkt hiermee mild; completeness mag leidend zijn.

## 10. Open risico's (eerlijk)

- Alleen de **remuneration**-bundel is empirisch bewezen; de andere 5 worden in taak 1 gevalideerd. Een bundel kan tegenvallen (bv. de Condition-zware arrangementen, of een te diep schema na inlining) → dan die bundel hand-tunen of verder splitsen.
- `build_section_schema` kan op een componenttype dezelfde API-muren raken als de verworpen full-schema-aanpak; daarom per-sectie validatie vóór gebruik, met hand-gebouwd schema als fallback (zoals de spike).
- Kostenraming is ruw; verifiëren tegen actuele gemini-3.5-flash-tarieven vóór een volledige 700-CAO-run.
