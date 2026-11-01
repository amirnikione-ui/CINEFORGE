.PHONY: help bootstrap api web worker test e2e lint clean

help:
	@echo "CINEFORGE dev commands"
	@echo "  make bootstrap   - create venvs and install deps (backend + web)"
	@echo "  make api         - run FastAPI on :8000"
	@echo "  make web         - run Next.js on :3000"
	@echo "  make worker      - run Celery worker (needs REDIS_URL)"
	@echo "  make test        - run backend + integration tests"
	@echo "  make e2e         - chat brief -> rendered mp4, no browser"

bootstrap:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
	cd apps/web && npm install --no-audit --no-fund

api:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

web:
	cd apps/web && npm run dev

worker:
	cd backend && . .venv/bin/activate && python -m workers.celery_app

test:
	cd backend && . .venv/bin/activate && pytest -q ../tests ../backend/tests

e2e:
	cd backend && . .venv/bin/activate && python ../scripts/demo_e2e.py
