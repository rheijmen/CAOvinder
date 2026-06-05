# CAO Centraal — Design: API-first dataproduct (deelproject 1)

**Datum:** 2026-06-03
**Status:** Goedgekeurd 2026-06-03 — beslispunten O1–O4 vastgelegd; O5/O6 worden in plan 1a/1b uitgewerkt
**Onderbouwing:** `docs/research/2026-06-03-cao-centraal-marktonderzoek.md`
**Scope:** Deelproject 1 van de herpositionering. Distributie/RSS/social (facet 6) en de HR Open export-mapping zijn aparte latere deelprojecten.

---

## 1. Context & doel

CAO Centraal wordt een **commercieel, API-first dataproduct** dat Nederlandse CAO-data gestructureerd ontsluit als databron voor payroll-, HR- en uitzendsoftware. Het marktgat (uit onderzoek, hoog vertrouwen): smalle uitzend-equal-pay-tools (CAOloon, CAOWijzer) enerzijds en portal-only brede bronnen zonder API (AWVN, XpertHR) anderzijds — **niemand biedt een brede, developer-first CAO-data-API**. Dat is de te bezetten positie.

Doel van deelproject 1: een productie-waardige, veilige, agent-vriendelijke API + MCP-server bovenop het bestaande canonieke datamodel, met onboarding, authenticatie en quota-/billing-enforcement die het vastgelegde pricing-model afdwingen.

## 2. Vastgelegde beslissingen (met onderbouwing)

| # | Beslissing | Onderbouwing |
|---|-----------|--------------|
| D1 | **SETU v2.0.0-rc.1 blijft het canonieke datamodel.** | Onderzoek (hoog vertrouwen): SETU modelleert de volledige NL CAO-beloningsrealiteit al (loonschalen, ORT/toeslagen, vakantietoeslag, vergoedingen, verlof, IKB, pensioen) met conditionele toepasbaarheid. HR Open Standards (`PayrollMasterData`) is gericht op werknemer-onboarding in payroll, niet op CAO-modellering. |
| D2 | **HR Open Standards = export-/interop-mapping**, geen kernschema. | Bewaart bewust de internationale-interop-hoek uit de oorspronkelijke opdracht ("*internationale* HR Open standards"), zonder het domeinmodel te verzwakken. Apart later deelproject. |
| D3 | **Positionering:** brede, sector-agnostische, API-first databron. | Open marktgat. |
| D4 | **Ontsluiting:** REST + OpenAPI (`/openapi.json|.yaml`) + `llms.txt`/`llms-full.txt` + **MCP-server** als eersteklas agent-kanaal. | Onderzoek (medium): standaard vindbare, machine-leesbare definities voor de nieuwe golf AI-apps. |
| D5 | **Security:** OWASP API Security Top 10 (2023). Per-object autorisatie (BOLA #1), verplichte rate limiting/quota (API4), API keys primair + OAuth2/OIDC voor partner/enterprise. | Onderzoek (hoog vertrouwen). |
| D6 | **Anti-misbruik:** progressive trust (anoniem demo → gratis key op zakelijk domein + e-mailverificatie + anti-sybil → KvK als escalatie). Quota op **organisatie-niveau**. Soft-close i.p.v. harde 403. | Brainstorm; "niet kloten"-principe + controle. |
| D7 | **Pricing:** Free / Per-CAO (€199/CAO/jaar) / Business (€399/mnd, per organisatie). Zie §9. | Vastgelegd in [[cao-centraal-pricing-model]]. |
| D8 | **Support altijd AI-assisted; uptime-SLA voor iedereen altijd.** | Brainstorm. |

## 3. Scope & decompositie

Deelproject 1 omvat 5+ subsystemen. Om de implementatieplannen behapbaar te houden, splitsen we de **bouw** in twee plannen (één gedeeld design doc):

- **Plan 1a — API-contract + datamodel-expositie + auth.** Read-only API bovenop het canonieke SETU-store, OpenAPI/llms.txt/MCP, authenticatie.
- **Plan 1b — Onboarding + quota/billing-enforcement.** Organisatie-accounts, progressive-trust onboarding, quota-metering, soft-close, tier-enforcement, betaalprovider-integratie.

Buiten scope van deelproject 1: distributie/RSS/social (facet 6), HR Open export-mapping (D2), de extractiepipeline zelf (bestaand; wél een afhankelijkheid — zie §11).

## 4. Architectuur

Het bestaande **dual-store-principe blijft** (SETU-beloningsregister ↔ statutory references, vergelijken at read time, nooit mergen). Daar bovenop komt een **read-only serving-laag**:

```
                         ┌─────────────────────────────┐
   AI-agents / LLM-apps ─┤  MCP-server (tools/resources)│┐
                         └─────────────────────────────┘│
   Software (payroll/HR)─┐                               ├─► API Gateway ─► Serving-laag ─► SETU-store (canoniek)
                         │  REST API (OpenAPI, JSON)     │   (auth, quota,                     ↕ read-time compare
                         └───────────────────────────────┘    rate limit,                    Statutory references
                                                              soft-close)                      Momenten-store (vooruitblik)
```

- **API Gateway / serving-laag:** authenticatie, per-object autorisatie (tenant-isolatie), rate limiting, quota-metering, soft-close, response-shaping. Leest uit de stores; muteert ze nooit.
- **MCP-server:** dezelfde serving-laag, andere interface. Coarse-grained tools/resources (zie §7) om call-inflatie te beperken.
- **Bestaande backend** (collection/OCR/extraction/compliance/Momenten) blijft de *productie* van data; de serving-laag is strikt consumptie.

## 5. Componenten & verantwoordelijkheden

| Component | Doet | Hangt af van |
|---|---|---|
| `serving` (nieuw) | Read-models + response-shaping over SETU/Statutory/Momenten | bestaande stores |
| `api` (uitbreiden) | REST-endpoints, OpenAPI, llms.txt | `serving`, `auth` |
| `mcp` (nieuw) | MCP-tools/resources | `serving`, `auth` |
| `auth` (nieuw) | API keys, OAuth2/OIDC, org-identiteit, progressive-trust verificatie | org-store |
| `accounts` (nieuw) | Organisaties, tiers, onboarding, KvK/domein-verificatie | betaalprovider |
| `metering` (nieuw) | Billable-operation telling, quota, soft-close, anomaliedetectie | `auth`, `accounts` |

Elk component: één duidelijk doel, eigen interface, los testbaar.

## 6. Datamodel-expositie & correctheid (KRITISCH)

- De API exposeert het **canonieke SETU-model** read-only. Geen nieuw schema; wel publieksvriendelijke read-models/serializers.
- **Correctheid-labeling als first-class API-veld** (`provenance`: `status` verified/unverified + `source` ai_extracted + `confidence`). Productfeature én aansprakelijkheidsschild; klanten kunnen filteren/alleen-geverifieerd opvragen.
- **ARCHITECTUUR (besloten 2026-06-03):** confidence/exception mag **NIET in het SETU-document** — de SETU-schema heeft 130× `additionalProperties: false` (ook top-level), dus extra velden breken de validatie. De pipeline strip ze nu juist bewust (`_remove_non_setu_properties`). Daarom: een **aparte `ProvenanceStore`** (sidecar JSON, los van de SETU-store, conform dual-store-principe) die de serving-laag **at read time joint** met het SETU-document. SETU blijft schoon/compliant.
- **Databron (beslissing O-correctheid = optie B):** de pipeline berekent al een confidence-signaal (`HybridExtractionResult.confidence_summary`, `table_extraction.confidence_score`) dat nu wordt **weggegooid**. Plan = dat signaal vastleggen in de ProvenanceStore i.p.v. extractie herbouwen. Voor de ~70 bestaande bestanden: backfill met baseline-provenance (source=ai_extracted, status=unverified) + table-confidence waar herafleidbaar, zonder volledige herverwerking.
- **Plansplitsing:** dit valt uiteen in **plan 1a-provenance** (model + ProvenanceStore + pipeline-wiring + backfill) en **plan 1a-api** (serving join + endpoints). De serving-laag leest provenance-if-present met neutrale fallback, zodat 1a-api los van 1a-provenance shipbaar is.

## 7. API-surface & de definitie van een "call"

**Coarse-grained, agent-vriendelijke endpoints** — bewust ontworpen zodat één logische vraag = één operatie, om call-inflatie bij MCP/agents te voorkomen:

- `GET /v1/cao/{id}` — volledig CAO-beloningsdocument in één response (niet 10 losse sub-fetches).
- `GET /v1/cao/{id}/salary-scales`, `/allowances`, … — deelresources voor wie gericht ophaalt.
- `GET /v1/cao?sector=&query=` — zoeken/lijst.
- `GET /v1/cao/{id}/changes?from=&horizon=` — **vooruitblik** op aankomende wijzigingen (Momenten).
- `GET /openapi.json|.yaml`, `/llms.txt`, `/llms-full.txt` — machine-leesbare discovery.
- MCP-tools spiegelen deze: `get_cao`, `search_caos`, `get_upcoming_changes` — coarse-grained.

**Billing-eenheid (BESLOTEN, O1):** een **"billable operation"** = één logische data-ophaling (één CAO-document, één zoekopdracht, één changes-query), **niet** één HTTP-/MCP-tool-call. Interne sub-fetches tellen als één. Free 1.000 operations/mnd; MCP krijgt een **ruimere allowance** (agents waaieren uit). Endpoints bewust coarse-grained zodat één operatie een heel CAO-document teruggeeft.

## 8. Security (secure by design)

- **AuthN:** API keys (server-to-server, primair) in header; OAuth2 auth-code+PKCE (third-party); OIDC (enterprise SSO). JWT met korte expiry intern.
- **AuthZ / tenant-isolatie:** per-object autorisatie afdwingen (BOLA #1). Elke resource-toegang gecheckt tegen org-scope.
- **Resource-controle:** verplichte rate limiting + quota per **organisatie** (API4). Voorkomt 5-keys-omzeiling.
- **Anti-sybil:** disposable-domein-block, e-mailverificatie, velocity/fingerprint (AVG: grondslag gerechtvaardigd belang, dataminimalisatie, bewaartermijn, vermeld in privacyverklaring).
- **Auditeerbaarheid:** toegangslogs per key/org.

## 9. Pricing & enforcement

| | Free "Proeven" | Per-CAO | Business |
|---|---|---|---|
| Prijs | €0 | €199/CAO/jaar | €399/maand (per org) |
| CAO's | 1 | 1–10 | Alle |
| Operations/mnd | 1.000 | tot 10.000 | Onbeperkt |
| Versheid | Wekelijks | Dagelijks | Dagelijks |
| Vooruitblik (Momenten) | — | Aankomend, ruim vooraf | Volledig + push/webhooks |
| Datadiepte | Volledig | Volledig | Volledig |
| OpenAPI + MCP | Sandbox | Productie | Productie |
| Historie/timeline | — | Beperkt | Volledig |
| Support | AI-assisted | AI-assisted | AI-assisted + e-mail |
| Uptime-SLA | ✅ Altijd | ✅ Altijd | ✅ Altijd |
| Anker | Progressive trust | Geverifieerd | KvK |

- **Escalatie → Business** bij >10 CAO's óf >10.000 operations/mnd. 2e CAO = meteen betaald (per CAO/jaar).
- **Soft-close:** bij limiet gracieus degraderen (melding + upgrade-prompt; data blijft aanwezig maar nudge-end), geen harde 403.
- **Billing-cadans (BESLOTEN, O4):** beide tiers bieden **maand én jaar**, met jaarkorting (~2 maanden gratis). Per-CAO ~€19/mnd of €199/jaar; Business €399/mnd of ~€3.990/jaar.
- **Gratis nieuwsfeed/e-mail** = publieke top-of-funnel (haak nu; uitwerking in facet-6-deelproject).

## 10. Correctheid, aansprakelijkheid & voorwaarden

- **Accuraatheids-disclaimer** + **aansprakelijkheidsplafond** in de API-voorwaarden (data voedt loonberekeningen → reëel risico bij fouten).
- **Correctie-/disputeproces:** klanten kunnen vermoedelijke fouten melden; SLA op behandeling (niet op uptime).
- **Correctheid-labeling** (§6) als zichtbaar onderdeel van het contract.
- **Doorverkoop-clausule:** embedded use in eigen software voor eigen eindklanten = toegestaan; ruwe dataset herdistribueren/doorverkopen of een concurrerende CAO-databron bouwen = niet toegestaan.

## 11. Datatoevoer-afhankelijkheid & versheid (RISICO)

Het pricing-model belooft "alle CAO's", "dagelijkse versheid" en "vooruitblik op wijzigingen". Huidige realiteit: ~70 CAO's via een dure 3-LLM-extractiepipeline. **Dit is een expliciete afhankelijkheid en risico**, geen aanname die de API-spec mag verbergen:

- **Lanceer-scope eerlijk afbakenen:** "alle CAO's" = de daadwerkelijk geïngeste set bij launch (start ~70, met ramp-plan), transparant gecommuniceerd.
- **Dagelijkse versheid + change-detection** is een data-ops-commitment dat apart belegd moet worden (raakt collection/extraction, buiten deelproject 1).
- De API-/MCP-contracten kunnen wél nu ontworpen worden; de *belofte-niveaus* (SLA op versheid/dekking) worden geschaald op de werkelijke toevoer.

## 12. Beslissingen & resterende open punten

**Besloten 2026-06-03 (Rik):**
- **O1 — "call" = billable operation** (niet HTTP/MCP-tool-call); ruimere MCP-allowance; coarse-grained endpoints. Zie §7.
- **O2 — Datatoevoer:** lanceer-beloften (dekking/versheid) schalen op werkelijke toevoer; data-ops (meer CAO's + dagelijkse verversing + wijzigingsdetectie) als **apart werkspoor**, buiten deelproject 1. Zie §11.
- **O3 — Free-tier-arbitrage: optie A** — lek bewust accepteren met rem. Free blijft op zakelijk domein, bewust mager (1 CAO, wekelijks, geen vooruitblik, 1.000 ops, alleen AI-support); ToS-verbod op multi-accounten + velocity/fingerprint-detectie van domein-farming. KvK blijft escalatie/upgrade-trigger, niet vereist voor free. Zie §8.
- **O4 — Billing-cadans:** maand én jaar op beide tiers, jaarkorting ~2 maanden (Per-CAO ~€19/mnd of €199/jaar; Business €399/mnd of ~€3.990/jaar). Zie §9.

**Resterend (uit te werken in de plannen, geen strategische beslissing nu):**
- **O5 — MCP-ontwerpdetails** (tool-/resource-granulariteit, auth, rate limiting voor agents) — plan 1a, evt. korte technische verkenning vooraf; onderzoek leverde hier geen geverifieerde best practices.
- **O6 — AVG-specifics** (multi-tenant isolatie-mechaniek, fingerprint-grondslag = gerechtvaardigd belang, bewaartermijnen, privacyverklaring) — plan 1b; mogelijk korte juridische check.

## 13. Teststrategie

- Per component los testbaar (§5). Contract-tests tegen OpenAPI-spec. Auth/authZ-tests incl. BOLA (cross-tenant toegang moet falen). Quota/soft-close-gedrag. MCP-tools tegen dezelfde serving-laag.

## 14. Out of scope (deelproject 1)

Distributie/RSS/social (facet 6, eigen onderzoek + spec); HR Open export-mapping (D2); wijzigingen aan de extractiepipeline (afhankelijkheid, §11); package-rename `cao_engine` → `cao_centraal` (mechanisch, eigen klein traject).
