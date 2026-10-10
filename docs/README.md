# Documentation

Source of truth for the project. The original documents are kept unchanged in [archive/](archive/) for
history; when they disagree with the documents below, **the documents below win**.

Business and finance documents are in French (the audience: founders, cooperatives, funders in Côte d'Ivoire).
Technical documents are in English (the audience: developers; code and API names are English).

## Business — `business/`

| Document | Content |
|---|---|
| [01-vision-produit.md](business/01-vision-produit.md) | Problem, promise, users, MVP scope |
| [02-marche-et-concurrence.md](business/02-marche-et-concurrence.md) | Market, competitors, blind spots, risks |
| [03-validation-terrain.md](business/03-validation-terrain.md) | Phase A: interview script, demo, go/no-go criteria |
| [04-acquisition.md](business/04-acquisition.md) | First 10 customers: pitch, field plan, objections, KPIs |
| [05-roadmap.md](business/05-roadmap.md) | Single roadmap aligned with the code |

## Finance — `finance/`

| Document | Content |
|---|---|
| [01-tarification.md](finance/01-tarification.md) | Pricing principles and grid |
| [02-previsionnel.md](finance/02-previsionnel.md) | Costs, corrected break-even, 3-year scenarios |
| [03-financement.md](finance/03-financement.md) | Funding programmes and need |

## Technical — `technical/`

| Document | Content |
|---|---|
| [01-architecture.md](technical/01-architecture.md) | Components, layering, environments |
| [02-features-and-screens.md](technical/02-features-and-screens.md) | Screens per app, role matrix |
| [03-api.md](technical/03-api.md) | API conventions, endpoint map, changes from v0 |
| [04-data-model.md](technical/04-data-model.md) | Tables, state machines |
| [05-offline-sync.md](technical/05-offline-sync.md) | Sync protocol, clock correction |
| [06-payments.md](technical/06-payments.md) | Payout flow, providers, webhook |
| [07-security-and-privacy.md](technical/07-security-and-privacy.md) | Auth, tenancy, personal data (ARTCI) |
| [08-development.md](technical/08-development.md) | Run, seed, test, migrate |
| [09-low-bandwidth.md](technical/09-low-bandwidth.md) | Compression, caching, slim sync — measured before/after |
| [adr/](technical/adr/) | Architecture decision records |

## What changed from the archive

| Archive problem | Resolved in |
|---|---|
| API spec cut off mid-JSON (payments), no reports/EUDR/buyer endpoints | technical/03-api.md + code |
| No lot entity, plots as points only | ADR 0002, ADR 0004, technical/04-data-model.md |
| Contradictory prices (10–50K / 20K / 25K, "paid pilot that is free") | finance/01-tarification.md |
| Break-even "15–20 cooperatives" (actually ~65–87) | finance/02-previsionnel.md |
| Cocoa price example 800 FCFA/kg (obsolete) | business/02-marche-et-concurrence.md |
| Two different sprint plans | business/05-roadmap.md |
| Sync "atomic" but per-item results; two idempotency mechanisms; 409 on replay | ADR 0005, technical/05-offline-sync.md |
| Role matrix contradicting the API | technical/02-features-and-screens.md |
| State traceability system and exporter tools missing from competition | business/02-marche-et-concurrence.md |
| Personal-data law not mentioned | technical/07-security-and-privacy.md |
| Citations [1]–[6] pointing nowhere | flagged "à re-sourcer" in business/finance docs |
