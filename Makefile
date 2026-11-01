.PHONY: help bootstrap api web test e2e smoke clean

help:
	@echo "CINEFORGE dev commands"
	@echo "  make bootstrap   - install backend deps + web deps"
	@echo "  make api         - run FastAPI on :8000 (backend/)"
	@echo "  make web         - run Next.js on :3000 (apps/web)"
	@echo "  make test        - full monorepo test suite (scripts/run_tests.sh)"
	@echo "  make e2e         - chat brief -> rendered mp4, zero API keys"
	@echo "  make smoke       - contract-path smoke test against a live API"

bootstrap:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
	cd apps/web && npm install --no-audit --no-fund

api:
	cd backend && uvicorn app.main:app --reload --port 8000

web:
	cd apps/web && npm run dev

test:
	bash scripts/run_tests.sh

e2e:
	cd backend && python ../scripts/demo_e2e.py

smoke:
	bash scripts/smoke_test.sh
