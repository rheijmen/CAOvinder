# Marktonderzoek CAO Centraal — diepgaand rapport

**Datum:** 2026-06-03
**Methode:** deep-research harness — 6 zoekhoeken, 25 bronnen opgehaald, 121 claims geëxtraheerd, top-25 adversarieel geverifieerd (2/3-stemmen om te verwerpen), 22 bevestigd / 3 verworpen, gesynthetiseerd tot 8 bevindingen.
**Scope:** Nederland. Doel: commercieel API-product dat NL CAO-data ontsluit als databron voor payroll-, HR- en uitzendsoftware.

---

## Managementsamenvatting

De Nederlandse CAO-datamarkt wordt gedomineerd door **workflow-/portaalproducten**, niet door **developer-first data-API's**. Dat laat een duidelijk gat voor CAO Centraal. De dichtstbijzijnde commerciële concurrenten — **CAOloon** (350+ CAO's, JSON-API, koppelingen met o.a. MySolution) en **CAOWijzer** (200+ CAO's, 1000+ gevolgd op mutaties, abonnementen €69/€99/€149 per maand per opdrachtgever) — zijn allebei **smal gericht op gelijkwaardige beloning voor de uitzendbranche**. Brede spelers als **AWVN Cao-kijker** en **XpertHR** zijn **portal-only zonder publieke API**, waardoor derden moeten screen-scrapen.

**Kritische bevinding (tegen de oorspronkelijke aanname in):** **SETU v2.0.0-rc.1 modelleert de volledige NL CAO-beloningsrealiteit al** (loonschalen, ORT/ploegen/overwerk, vakantietoeslag, vergoedingen, bijzondere beloningen, verlof, IKB, pensioen) met gestructureerde, conditionele toepasbaarheid (leeftijd, functie, trede). **HR Open Standards is een zwakkere fit**: de `PayrollMasterData`-structuur richt zich op het *onboarden van een werknemer in een payrollsysteem*, niet op het modelleren van een collectieve arbeidsovereenkomst. → **Aanbeveling: houd SETU als canoniek datamodel; behandel HR Open Standards als export-/interop-doel (PayrollMasterData-mapping) voor payroll-integrators.**

---

## Facet 1 — Concurrentie

**Bevinding (hoog vertrouwen):** CAOloon en CAOWijzer zijn smal gericht op gelijkwaardige beloning/inlenersbeloning voor de uitzendbranche, niet op algemene CAO-data.
- **CAOloon:** 350+ CAO's; JSON-API met producten "API per call / Json Maand / Json Uur"; kant-en-klare koppelingen (partner-bevestigd: MySolution). Positionering: "Met Inlenersportaal.com kan de inlener de gelijkwaardige beloning snel en eenvoudig aan de uitlener verstrekken."
- **CAOWijzer:** 200+ CAO's (1000+ gevolgd op loonmutaties), inclusief periodieken/toeslagen/vergoedingen; API om data in eigen systeem op te slaan; PDF-export. Abonnementen: Light €69 (10 opdrachtgevers, €10,93/extra), Standard €99 (25, €6,15/extra, "POPULAIR"), Premium €149 (75, €3,08/extra).
- *Context:* ABU/NBBU verschoven "inlenersbeloning" → "gelijkwaardige beloning" per 1 jan 2026.
- **Bronnen:** caoloon.com, handleiding.caoloon.com, mysolution.com, caowijzer.com, caowijzer.com/abonnementen

**Bevinding (hoog vertrouwen):** Brede CAO-informatiebronnen zijn portal-only zonder API → marktgat.
- **AWVN Cao-kijker:** "de gratis online informatiebron van AWVN over recente cao-ontwikkelingen" — portaal met infographics/nieuws/zoeken, géén API/export/machine-readable download.
- **XpertHR CAO** (~2.000 overeenkomsten, grootste gestructureerde DB): geen native publieke API, dwingt derden tot screen-scraping ("software robots").
- **Verworpen claim (1-2):** dat Cao-kijker "alle CAO's" zou dekken als comprehensive repository — niet bevestigd.
- **Bronnen:** awvn.nl/cao/online-producten/cao-kijker, awvn.nl/online-producten, brixxs.com

> **Marktgat:** een brede, sector-agnostische, **developer-first / API-first** CAO-databron is genuinely onderbediend.

---

## Facet 2 — HR Open Standards vs SETU

**Bevinding (hoog vertrouwen):** SETU v2.0.0-rc.1 is een sterke domein-fit. Dekt loonstructuur/schalen, toeslagen (overwerk/ploegen/ORT), vakantietoeslag, vergoedingen (woon-werk/thuiswerk/standby), bijzondere beloningen, verlof, IKB, pensioen. Gebruikt gestructureerde condities (Age, EmploymentDuration, Occurence, PositionProfile/functie, SalaryScale, Text + AllOf/AnyOf/Not) via een `conditionType`-discriminator. Mapt schoon op loongebouw, functiegroepen, tredes, leeftijdsgebonden loon.
- **Bronnen:** standard.setu.nl/docs/gelijkwaardige-beloning + lokale `setu_v2.0.0-rc.1.json`

**Bevinding (medium vertrouwen):** HR Open Standards is een zwakkere fit. `PayrollMasterData` (betaalgegevens, inhoudingen, beslagleggingen, belastingen, met NL-lokalisatie) is gericht op werknemer-onboarding in payroll, niet op CAO-modellering.
- **Verworpen (1-2):** dat HR Open een dedicated "Compensation & Benefits"-domein met 4.4-flexibiliteit voor complexe plannen heeft.
- **Verworpen (0-3):** dat de beste docs achter een paywall zitten (publieke evaluatie is dus wél mogelijk).
- **Migratiepad:** SETU canoniek houden; HR Open Standards PayrollMasterData-mapping aanbieden als export voor payroll-integrators.
- **Bronnen:** hropenstandards.org/standards, /documentation

---

## Facet 3 — Moderne ontsluiting (REST + MCP + AI)

**Bevinding (medium vertrouwen):** Serveer machine-leesbare API-definities op standaard vindbare paden: `/openapi.json` of `/openapi.yaml` voor de volledige spec, plus `llms.txt` (compacte markdown-index met links) en `llms-full.txt` (volledige ingebedde inhoud). AI-agents lezen de samenvatting en volgen de links; markdown omzeilt HTML/CSS/JS-ruis.
- *Caveat:* alleen `/llms.txt` is formeel geratificeerd (llmstxt.org, Answer.AI sep 2024); `llms-full.txt` en het "standaardpad"-frame zijn de-facto conventies (Mintlify/Fern/Anthropic). Bronnen zijn vendor-blog-kwaliteit → medium.
- **Ontwerpimplicatie:** ship OpenAPI + llms.txt/llms-full.txt, semantische endpoints, en overweeg **MCP als eersteklas kanaal** voor AI-agents.
- **Bronnen:** buildwithfern.com, llmstxt.org, answer.ai

> *Open:* MCP-specifieke ontwerpdetails (tool-/resource-design, auth, rate limiting voor agents) leverden geen geverifieerde claims op — moet nog uitgewerkt.

---

## Facet 4 — Secure by design

**Bevinding (hoog vertrouwen):** Baseer beveiliging op de OWASP API Security Top 10 (2023):
- **BOLA (API1:2023, Broken Object Level Authorization)** is risico #1 — API's exposen object-identifiers met een breed access-control-aanvalsoppervlak → **per-object autorisatie / multi-tenant isolatie afdwingen**.
- **Unrestricted Resource Consumption (API4:2023)** maakt **rate limiting + resource-limieten verplicht**.
- **Auth context-specifiek:** API keys (server-to-server) als primaire credential; OAuth 2.0 (auth-code + PKCE) voor third-party apps; JWT (korte expiry) voor microservices; OpenID Connect voor enterprise SSO.
- **Bronnen:** owasp.org/API-Security/2023, buildwithfern.com

> *Open:* AVG/GDPR-specifieke eisen, multi-tenant isolatie-mechaniek en auditability leverden geen specifieke geverifieerde claims op (alleen generiek OWASP/auth).

---

## Facet 5 — Pricing & free tier

**Bevinding (hoog vertrouwen):** Een genereuze, value-first freemium ("hack for free, pay for production") is het bewezen patroon. Algolia's gratis "Build"-plan geeft 1 miljoen records (100× sprong van 10.000) met volledige platform-features, en rekent pas op productieschaal. Een effectieve free tier moet **kernwaarde vroeg demonstreren** en een echt probleem oplossen, met bewuste limieten (volume, features, support, snelheid) die natuurlijke upgrade-druk creëren.
- **Ontwerpimplicatie:** free tier toont echte CAO-lookups/gestructureerde data vroeg (de "magic"), met limieten op call-volume, aantal CAO's/opdrachtgevers, of versheid die productiegebruikers natuurlijk ontgroeien.

**Bevinding (hoog vertrouwen):** Freemium-economie stelt randvoorwaarden: alleen houdbaar bij zeer lage marginale kosten per gebruiker (geldt voor digitale data). Conversie free→paid is doorgaans **enkele procenten** (mediaan B2B-SaaS 2-5%; sales-assisted 10-15%), dus betekenisvolle omzet vereist **volume**. → maak de funnel breed; zorg dat de betaal-trigger (productievolume, meer CAO's/opdrachtgevers, SLA, versheid, MCP/agent-toegang) overtuigend is.
- **Bronnen:** algolia.com (persbericht), stripe.com/resources (freemium), zuplo/moesif/userpilot (2026)

---

## Facet 6 — Distributie & community

> **Onderbelicht in dit onderzoek:** dit facet leverde geen overlevende geverifieerde claims op binnen het budget. Wel opgehaalde (niet-geverifieerde) bronnen: salarisvanmorgen.nl/adverteren, awvn.nl/awvn-in-het-nieuws, daily.dev B2B-developer-marketing. **Aanbeveling: aparte, gerichte vervolgronde** voor RSS/nieuwsfeed-mechanismen en het social-/nieuwskanaal voor de branche.

---

## Caveats (belangrijk)

1. CAOloon-homepage was JS-rendered/geblokkeerd; positionering bevestigd via docs-subdomein + partnersites. De "Maand/Uur/per-call"-dimensie verwart mogelijk loontabel-producten (maand- vs uurloon) met facturatiecadans — alleen "per call" is zeker.
2. CAOWijzer's API-specpagina gaf 404; auth/endpoints/API-prijs niet onafhankelijk geverifieerd — alleen dát er een API is.
3. llms.txt/AI-distributie leunt op vendor-blogs + het llmstxt.org-voorstel; alleen `/llms.txt` is geratificeerd.
4. Freemium-conversie/volume zijn algemene SaaS-consensus, niet CAO-data-specifiek.
5. HR Open Standards-fit is slechts deels vastgesteld uit publieke docs; twee gerelateerde claims werden verworpen — **neem niet aan dat HR Open een kant-en-klaar CAO-compensatiemodel biedt.**
6. **Tijdgevoelig:** prijzen, SETU-versie (rc.1, mrt 2026) en de ABU/NBBU-terminologieshift (1 jan 2026) zijn actueel medio 2026 maar verschuiven.

## Open vragen (voor vervolgonderzoek)

1. Werkelijke dekking, versheid en API-prijs van XpertHR/Visma en de FNV/CNV-vakbondsdatabanken — heeft iemand een echte publieke API die ons gat verkleint?
2. Hoe ontwerp je MCP concreet als eersteklas distributiekanaal voor CAO-data (tools/resources, auth, rate limiting)?
3. Specifieke AVG/GDPR-, multi-tenant-isolatie- en auditability-eisen voor een commerciële CAO-data-API.
4. Facet 6: welke RSS/nieuwsfeed- en social-mechanismen gebruiken AWVN/FNV/flexnieuws, en wat maakt CAO Centraal dé default nieuwsbron?

---

## Concrete aanbevelingen voor CAO Centraal

1. **Positionering:** brede, sector-agnostische, **API-first** CAO-databron — het open marktgat tussen smalle uitzend-equal-pay-tools (CAOloon/CAOWijzer) en portal-only brede bronnen (AWVN/XpertHR).
2. **Datamodel:** **SETU v2.0.0-rc.1 blijft canoniek.** HR Open Standards (PayrollMasterData) als **export-/interop-mapping**, niet als kernschema. → *Dit weerspreekt de oorspronkelijke opdracht om SETU helemaal los te laten; bespreken.*
3. **Ontsluiting:** REST met OpenAPI op `/openapi.json|.yaml`, plus `llms.txt`/`llms-full.txt` en een **MCP-server** als agent-kanaal.
4. **Security:** OWASP-2023-gedreven; per-object autorisatie (multi-tenant), verplichte rate limiting/quota, API keys primair + OAuth2/OIDC voor partner/enterprise.
5. **Pricing:** genereuze free tier (echte lookups, "magic" vroeg voelbaar) met volume-/CAO-/versheid-limieten; betaalde triggers = productievolume, meer opdrachtgevers, SLA, versheid, MCP/agent-toegang. Brede funnel (lage conversie).
6. **Distributie:** apart vervolgonderzoek voor RSS/nieuwsfeed + branche-nieuwskanaal.
