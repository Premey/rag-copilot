# RAG Copilot

A conversational AI that answers questions grounded in your document knowledge base — with cited sources and relevance scores. No hallucination.

## Stack
- **Backend:** Python 3.11, FastAPI, ChromaDB, LangChain, OpenAI
- **Frontend:** React 18 + Vite + TypeScript
- **Auth:** JWT

## Quick Start
```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env   # add OPENAI_API_KEY
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install && npm run dev
```

## Docs
- [`docs/architecture.md`](docs/architecture.md) — System design & user flow
- [`docs/api_contract.md`](docs/api_contract.md) — All endpoint specs  
- [`docs/rag_pipeline.md`](docs/rag_pipeline.md) — Pipeline deep-dive
