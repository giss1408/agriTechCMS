# Backend — Cabosse API

FastAPI + SQLAlchemy 2 (async) + Alembic. PostgreSQL in production, SQLite for demos and tests.

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp .env.example .env
.venv/bin/python -m app.seed --reset     # demo data
.venv/bin/uvicorn app.main:app --reload  # http://localhost:8000/docs
.venv/bin/pytest -q
```

Layout: `app/api` (HTTP), `app/services` (business rules), `app/models.py`, `app/schemas.py`, `app/core`
(config, security, errors, geo, time). Read [docs/technical](../../docs/technical) first.
