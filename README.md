# agriTechCMS — Cabosse

**Cabosse** is a collection, payment and traceability tool for agricultural cooperatives in Côte d'Ivoire
(cocoa first, cashew next). The name is French for *cocoa pod*.

- **Collectors** record each weighing on an Android phone in under a minute, **even without network**.
- **Managers** validate deliveries, pay producers by **mobile money** (advances deducted automatically) and
  follow the campaign on a dashboard.
- **Buyers** open a **traceability page per lot**: producers, geolocated parcels, EUDR completeness, GeoJSON export.
- **Producers** check their balance and last deliveries by **USSD**, from any phone.
- **Anyone can report a problem** — collectors (even offline), managers, producers by USSD, buyers from a lot page —
  into one inbox the cooperative handles.

> Status: **MVP for field validation** (Phase A of [the roadmap](docs/business/05-roadmap.md)).
> It runs end to end on a laptop with a realistic demo cooperative, to be shown to cooperative leaders
> before investing in the pilot. Built for 2G/3G links: a routine phone sync costs ~0.2 KB
> ([details](docs/technical/09-low-bandwidth.md)).

## Repository

| Path | What |
|---|---|
| [apps/backend](apps/backend) | API — FastAPI, PostgreSQL/SQLite, Alembic, 29 tests |
| [apps/web-admin](apps/web-admin) | Manager web app + public buyer page — React, TypeScript, Vite |
| [apps/mobile-collector](apps/mobile-collector) | Collector app — Flutter, offline-first (SQLite outbox) |
| [docs/business](docs/business) | Vision, market, field validation, acquisition, roadmap (FR) |
| [docs/finance](docs/finance) | Pricing, forecast and break-even, funding (FR) |
| [docs/technical](docs/technical) | Architecture, API, data model, sync, payments, security, ADRs (EN) |
| [docs/archive](docs/archive) | Original documents, unchanged |

## Quick start

```bash
make setup   # Python venv, npm install, flutter pub get
make seed    # demo cooperative: 40 producers, 2 weeks of deliveries, a sealed lot, payments
make api     # http://localhost:8000/docs
make web     # http://localhost:5173 → phone 07 00 00 00 01, the code is displayed (demo mode)
make mobile  # emulator/phone → phone 07 00 00 00 02
make test
```

Details: [docs/technical/08-development.md](docs/technical/08-development.md).

## Demo script (10 minutes, for cooperative meetings)

1. Phone in airplane mode → scan a producer card → enter 120 kg, quality A → *Valider la pesée*.
2. Airplane mode off → the delivery appears in the web app (*Collectes*, badge "À valider").
3. Validate it → *Lots* → add to a lot → *Sceller* → open *Page acheteur*.
4. *Paiements* → select the producer → *Payer la sélection* → *Paramètres → SMS envoyés*: the producer's confirmation.
5. `curl -X POST "localhost:8000/v1/channels/ussd?key=dev-ussd-key" -d phoneNumber=<producer phone> -d text=1` → the producer's balance;
   `-d "text=4*1"` → the producer disputes a weight, which appears in *Signalements*. Resolve it there: the producer gets an SMS.
