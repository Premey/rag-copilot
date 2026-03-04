# 🤖 RAG Copilot

A conversational AI that answers questions grounded in your document knowledge base — with cited sources and relevance scores. **No hallucination.**

> Ask a question → Retrieve relevant chunks → Generate a grounded answer → See the sources that backed it.

---

## ✨ Features

- **JWT Authentication** — Secure signup/login with hashed passwords
- **Hybrid Retrieval** — Combines FAISS vector similarity with BM25 keyword search
- **Source Citations** — Every answer includes the exact chunks + relevance scores
- **Low-Context Detection** — Gracefully handles questions outside the knowledge base
- **Observability** — Built-in metrics endpoint for query counts, latencies, success rates
- **Modern React UI** — Login, chat interface, source cards, loading/error states

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                   │
│                    React 18 + Vite + React Router                       │
│                                                                         │
│   ┌───────────┐    ┌───────────────────┐    ┌────────────────────┐      │
│   │  Login /  │───▶│  Chat Interface   │───▶│  Source Cards      │      │
│   │  Signup   │    │  (ask questions)  │    │  (cited chunks)    │      │
│   └───────────┘    └────────┬──────────┘    └────────────────────┘      │
│                             │ API calls (fetch)                          │
└─────────────────────────────┼────────────────────────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   FastAPI Backend   │
                    │    (Python 3.11)    │
                    ├────────────────────┤
                    │   /auth/*          │──▶ JWT + bcrypt + SQLite
                    │   /rag/ingest      │──▶ Load → Chunk → Embed → Store
                    │   /rag/ask         │──▶ Retrieve → Prompt → LLM
                    │   /rag/retrieve    │──▶ Debug retrieval (no LLM)
                    │   /rag/metrics     │──▶ Observability counters
                    │   /health          │──▶ Liveness check
                    └───────┬────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
      ┌──────────┐   ┌──────────┐   ┌──────────┐
      │  SQLite  │   │  FAISS   │   │  Gemini  │
      │  (users) │   │  + BM25  │   │  Flash   │
      └──────────┘   │ (vectors)│   │  (LLM)   │
                     └──────────┘   └──────────┘
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, Uvicorn |
| Vector DB | FAISS (dense) + BM25 (sparse) hybrid |
| Embeddings | `all-MiniLM-L6-v2` (sentence-transformers) |
| LLM | Google Gemini 2.0 Flash |
| Auth | JWT (python-jose) + bcrypt |
| User DB | SQLite via SQLAlchemy |
| Frontend | React 18, Vite, React Router |
| Linting | Ruff (Python) |

---

## 🚀 Quick Start (Local)

### Prerequisites

- Python 3.11+
- Node.js 18+
- A [Google AI API key](https://aistudio.google.com/apikey)

### 1. Clone & Setup Backend

```bash
git clone https://github.com/your-username/rag-copilot.git
cd rag-copilot

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env → set GOOGLE_API_KEY=your-key-here
```

### 2. Setup Frontend

```bash
cd frontend
npm install
```

### 3. Run

```bash
# Terminal 1 — Backend (from /backend)
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend (from /frontend)
npm run dev
```

Open **http://localhost:5173** → Sign up → Start asking questions!

> **Note:** Before asking questions, ingest the docs by calling `POST /rag/ingest` (see API Endpoints below).

---

## 📡 API Endpoints

> **Base URL:** `http://localhost:8000` (local) or your deployed Render URL  
> **Auth:** Bearer JWT in `Authorization` header (except `/health`, `/auth/*`)  
> **Content-Type:** `application/json`

### Endpoint Summary

| Method | Path | Auth | Purpose |
|--------|------|------|---------| 
| `GET` | `/health` | No | Service liveness check |
| `POST` | `/auth/signup` | No | Register new user |
| `POST` | `/auth/login` | No | Login → JWT token |
| `GET` | `/auth/me` | Yes | Current user profile |
| `POST` | `/rag/ingest` | Yes | Rebuild vector index from docs |
| `POST` | `/rag/ask` | Yes | Question → Answer + Sources |
| `POST` | `/rag/retrieve` | Yes | Debug: retrieval only (no LLM) |
| `GET` | `/rag/metrics` | Yes | Observability counters |

### Sample `curl` Commands

#### Health Check
```bash
curl http://localhost:8000/health
# → {"status":"ok","version":"1.0.0","timestamp":"..."}
```

#### Sign Up
```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"Str0ngPass!","full_name":"Jane Doe"}'
```

#### Login (get token)
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"Str0ngPass!"}'
# → {"access_token":"eyJ...","token_type":"bearer","expires_in":86400,...}
```

#### Ingest Documents
```bash
TOKEN="eyJ..."  # from login response

curl -X POST http://localhost:8000/rag/ingest \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force_rebuild":true}'
# → {"status":"success","docs_processed":20,"chunks_created":150,...}
```

#### Ask a Question
```bash
curl -X POST http://localhost:8000/rag/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"How do I reset my CloudDesk API key?","top_k":5}'
# → {"answer":"...","sources":[{"title":"...","score":0.92,...}],"status":"ok",...}
```

#### Debug Retrieval (no LLM)
```bash
curl -X POST http://localhost:8000/rag/retrieve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"billing FAQ","top_k":3}'
```

---

## 📥 Ingestion Flow

```
backend/data/docs/
  ├── doc_001_getting_started.json
  ├── doc_002_billing_faq.json
  ├── ...
  └── doc_020_*.json / .md

        │  POST /rag/ingest
        ▼
  ┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐     ┌───────────┐
  │  1. LOAD         │────▶│  2. CHUNK        │────▶│  3. EMBED        │────▶│  4. STORE  │
  │  Read .json/.md  │     │  500 tokens      │     │  MiniLM-L6-v2   │     │  FAISS     │
  │  Extract title,  │     │  50 overlap      │     │  384-dim vectors │     │  + BM25    │
  │  content, doc_id │     │  LangChain       │     │  per chunk       │     │  index     │
  └─────────────────┘     └─────────────────┘     └──────────────────┘     └───────────┘
```

### Query Pipeline (per `/rag/ask` call)

1. **Embed query** — same `all-MiniLM-L6-v2` model
2. **Hybrid retrieve** — 70% FAISS cosine similarity + 30% BM25 keyword match → top-5 chunks
3. **Guardrail check** — if best score < 0.50 → return `"status": "low_context"` (no hallucination)
4. **Build prompt** — system instructions + retrieved context + user question
5. **LLM generation** — Gemini 2.0 Flash (temperature=0.2, max 1024 tokens)
6. **Format response** — JSON with answer, sources, scores, trace_id, latency_ms

### Evaluation Method

- **Low-context detection**: Questions outside the knowledge base are caught when no chunk scores above the 0.50 threshold
- **Hybrid retrieval**: Combining dense (FAISS) and sparse (BM25) retrieval improves recall across both semantic and keyword-match queries
- **Metrics endpoint** (`/rag/metrics`): Tracks total queries, success rate, average latency, and low-context rate for ongoing quality monitoring

---

## ☁️ Deployment

### Backend → Render (or any Docker host)

1. Push your repo to GitHub
2. Create a new **Web Service** on [Render](https://render.com)
3. Set the **Root Directory** to `backend`
4. Render auto-detects the `Dockerfile`
5. Add **Environment Variables**:
   - `SECRET_KEY` — a long random string
   - `GOOGLE_API_KEY` — your Gemini API key
   - `FRONTEND_ORIGIN` — your deployed frontend URL (e.g. `https://rag-copilot.vercel.app`)
   - `DATABASE_URL` — `sqlite:///./clouddesk.db` (or a Postgres URL)
6. Deploy → note the backend URL (e.g. `https://rag-copilot-backend.onrender.com`)

### Frontend → Vercel

1. Create a new project on [Vercel](https://vercel.com), import your repo
2. Set **Root Directory** to `frontend`
3. Framework: **Vite** (auto-detected)
4. Add **Environment Variable**:
   - `VITE_API_URL` = your Render backend URL (e.g. `https://rag-copilot-backend.onrender.com`)
5. Deploy → frontend is live!

### Verify End-to-End

```bash
# Check backend health
curl https://rag-copilot-backend.onrender.com/health

# Sign up via deployed backend
curl -X POST https://rag-copilot-backend.onrender.com/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test1234!","full_name":"Test User"}'
```

---

## 🧪 Quality Gate

### Run Tests

```bash
# Run all backend tests
make test

# Or directly
cd backend && python -m pytest tests/ -v
```

### Lint & Format

```bash
# Check for lint errors
make lint

# Auto-format code
make format
```

### All Makefile Targets

| Target | Description |
|--------|-------------|
| `make install` | Install backend + frontend dependencies |
| `make lint` | Run ruff linter on Python code |
| `make format` | Auto-format Python code with ruff |
| `make test` | Run pytest on backend tests |
| `make dev-backend` | Start FastAPI dev server |
| `make dev-frontend` | Start Vite dev server |
| `make build-frontend` | Build frontend for production |
| `make docker-build` | Build backend Docker image |
| `make docker-run` | Run backend in Docker container |

---

## 📁 Project Structure

```
rag-copilot/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py             # /auth/* routes
│   │   │   └── rag.py              # /rag/* routes
│   │   ├── core/
│   │   │   ├── config.py           # env settings (pydantic)
│   │   │   ├── database.py         # SQLAlchemy engine
│   │   │   ├── deps.py             # FastAPI dependencies
│   │   │   ├── embeddings.py       # sentence-transformers client
│   │   │   ├── metrics.py          # observability counters
│   │   │   └── security.py         # JWT helpers
│   │   ├── models/
│   │   │   └── user.py             # SQLAlchemy user model
│   │   ├── schemas/
│   │   │   ├── auth.py             # auth request/response schemas
│   │   │   └── rag.py              # RAG request/response schemas
│   │   ├── services/
│   │   │   ├── auth_service.py     # signup/login logic
│   │   │   └── rag_service.py      # ingest/retrieve/ask logic
│   │   └── main.py                 # FastAPI app entry point
│   ├── data/docs/                  # Source documents (JSON/MD)
│   ├── tests/                      # pytest test suite
│   ├── Dockerfile                  # Container build
│   ├── requirements.txt            # Python dependencies
│   ├── pyproject.toml              # Ruff config
│   └── .env.example                # Environment template
├── frontend/
│   ├── src/
│   │   ├── api.js                  # API client (fetch-based)
│   │   ├── context/AuthContext.jsx  # Auth state management
│   │   ├── components/             # Reusable UI components
│   │   └── pages/                  # Login, Chat pages
│   ├── vercel.json                 # Vercel deployment config
│   ├── vite.config.js              # Vite dev server config
│   └── .env.example                # Frontend env template
├── docs/
│   ├── architecture.md             # System design & user flow
│   ├── api_contract.md             # Full endpoint specs
│   └── rag_pipeline.md             # Pipeline deep-dive
├── Makefile                        # lint, test, format, dev commands
└── README.md                       # ← You are here
```

---

## 📚 Docs

- [Architecture Overview](docs/architecture.md) — System design, user journey, tech decisions
- [API Contract](docs/api_contract.md) — All endpoint specs with request/response examples
- [RAG Pipeline Deep Dive](docs/rag_pipeline.md) — Ingestion, retrieval, and LLM generation details

---

## 📄 License

MIT
