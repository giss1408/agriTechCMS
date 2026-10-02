# One-word commands. See docs/technical/08-development.md.
BACKEND := apps/backend
WEB     := apps/web-admin
MOBILE  := apps/mobile-collector
PY      := $(BACKEND)/.venv/bin

.PHONY: setup seed api web mobile test test-backend test-web test-mobile db

setup:
	cd $(BACKEND) && python3 -m venv .venv && .venv/bin/pip install -q -e ".[dev]"
	cd $(WEB) && npm install
	cd $(MOBILE) && flutter pub get

seed:            ## demo cooperative (resets the local database)
	cd $(BACKEND) && .venv/bin/python -m app.seed --reset

api:
	cd $(BACKEND) && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

web:
	cd $(WEB) && npm run dev

mobile:
	cd $(MOBILE) && flutter run

db:              ## PostgreSQL in Docker
	docker compose up -d db

test: test-backend test-web test-mobile

test-backend:
	cd $(BACKEND) && .venv/bin/pytest -q

test-web:
	cd $(WEB) && npm run typecheck

test-mobile:
	cd $(MOBILE) && flutter analyze && flutter test
