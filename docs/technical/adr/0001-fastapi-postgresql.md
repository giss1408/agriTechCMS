# 0001 — FastAPI + PostgreSQL for the API

**Context.** The archive left the choice open between NestJS and FastAPI. The founder already runs FastAPI
services (djassa backend: OTP login, Celery, Alembic), and the domain is CRUD + business rules + reporting.

**Decision.** Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, PostgreSQL in production. SQLite for local
demos and tests (the same code runs on both thanks to a UTC datetime type and JSON columns).

**Consequences.** One language for API, seed scripts and data work (reports, EUDR exports, later satellite
checks). OpenAPI documentation for free at `/docs`. Background work starts with FastAPI background tasks;
move to a queue (Celery/RQ/Arq) when payouts or SMS volumes require retries across restarts.
