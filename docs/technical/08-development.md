# Development guide

## Prerequisites

Python 3.11+, Node 20+, Flutter 3.24+ (Android SDK for the app), Docker (optional, for PostgreSQL).

## Run everything locally (demo)

```bash
make setup     # venv + pip install, npm install, flutter pub get
make seed      # demo cooperative in apps/backend/agritech.db (resets it)
make api       # http://localhost:8000  (OpenAPI: /docs)
make web       # http://localhost:5173  — log in with 07 00 00 00 01, the code is shown on screen
make mobile    # flutter run on a connected device / emulator
```

Demo accounts (created by the seed):

| Phone | Role | Use |
|---|---|---|
| 07 00 00 00 01 | super admin | web dashboard |
| 07 00 00 00 02 | collector | mobile app |
| 07 00 00 00 03 | collector | mobile app |

The mobile app reaches the API at `http://10.0.2.2:8000/v1` (Android emulator → host). On a real phone during
a demo, put the laptop and phone on the same Wi-Fi and run:

```bash
cd apps/mobile-collector && flutter run --dart-define=API_URL=http://<laptop-ip>:8000/v1
```

USSD simulation:

```bash
curl -X POST "localhost:8000/v1/channels/ussd?key=dev-ussd-key" -d phoneNumber=<producer phone> -d text=1
```

## With PostgreSQL

```bash
docker compose up -d db
export AGT_DATABASE_URL=postgresql+asyncpg://agritech:agritech@localhost:5432/agritech AGT_AUTO_CREATE_SCHEMA=false
cd apps/backend && .venv/bin/alembic upgrade head && .venv/bin/python -m app.seed
```

`docker compose up` runs the database and the API together.

## Tests and checks

```bash
make test      # backend pytest + web typecheck + flutter analyze/test
```

| Suite | Covers |
|---|---|
| `apps/backend/tests` | gzip responses and uploads, ETag/304, slim pull and `ref_hash`, problem reports on every channel (idempotency, tenancy, USSD + SMS on resolution, public cap), OTP login and throttling, roles, server-side pricing with dated prices, idempotent replay, business rules, sync push (mixed batch, clock correction), incremental pull, audit, tenant isolation, parcel area and EUDR flags, lot lifecycle and public trace, payments with advances / failure / cancel, webhook signature and idempotency, USSD, dashboard and exports |
| `apps/mobile-collector/test` | QR parsing, decimal input, price-on-date (same rule as server), FCFA formatting, phone normalisation |

## Migrations

```bash
cd apps/backend
AGT_DATABASE_URL=... .venv/bin/alembic revision --autogenerate -m "describe change"
AGT_DATABASE_URL=... .venv/bin/alembic upgrade head
```

## Configuration

All backend settings are `AGT_*` environment variables — see `apps/backend/.env.example` and `app/config.py`.
Web: `VITE_API_URL`. Mobile: `--dart-define=API_URL=…`.
