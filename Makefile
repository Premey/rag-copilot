# ─── RAG Copilot ── Makefile ──────────────────────────────────────────────────

.PHONY: install install-backend install-frontend lint format test dev dev-backend dev-frontend build-frontend

# ── Install ──────────────────────────────────────────────────────────────────
install: install-backend install-frontend

install-backend:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

# ── Quality ──────────────────────────────────────────────────────────────────
lint:
	cd backend && python -m ruff check app/ tests/

format:
	cd backend && python -m ruff format app/ tests/

test:
	cd backend && python -m pytest tests/ -v

# ── Dev Servers ──────────────────────────────────────────────────────────────
dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

# ── Build ────────────────────────────────────────────────────────────────────
build-frontend:
	cd frontend && npm run build

# ── Docker ───────────────────────────────────────────────────────────────────
docker-build:
	cd backend && docker build -t rag-copilot-backend .

docker-run:
	cd backend && docker run -p 8000:8000 --env-file .env rag-copilot-backend
