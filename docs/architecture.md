# RAG Copilot — Day 1 Architecture Overview

> **Date:** 2026-03-02  
> **Goal:** Define the complete system scope, user journey, RAG pipeline, and API contract so any engineer can pick this up and build immediately.

---

## 1. What We're Building

A **RAG Copilot** — a conversational AI that answers questions grounded exclusively in a curated document dataset. No hallucination. Every answer includes cited source chunks with relevance scores.

**Core Value Proposition:**
- User asks a question in natural language
- System retrieves the most relevant document chunks from a vector store
- LLM synthesizes a grounded answer, citing exact sources
- User sees the answer AND the source snippets that backed it

---

## 2. User Journey

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐     ┌─────────────────────────┐
│  Landing /   │────▶│  Auth Screen │────▶│  Dashboard           │────▶│  Ask Question           │
│  Login Page  │     │  (signup /   │     │  - Sidebar: history  │     │  - Text input           │
│              │     │   login)     │     │  - Welcome prompt    │     │  - Send button          │
└──────────────┘     └──────────────┘     └──────────────────────┘     └───────────┬─────────────┘
                                                                                    │
                                                                                    ▼
                                                                        ┌─────────────────────────┐
                                                                        │  View Answer + Sources   │
                                                                        │  - LLM answer text      │
                                                                        │  - Source cards:        │
                                                                        │    title, chunk, score  │
                                                                        │  - Status badge         │
                                                                        │    (ok / low_context)   │
                                                                        └─────────────────────────┘
```

### Journey Steps Explained

| Step | Screen | User Action | System Response |
|------|--------|-------------|-----------------|
| 1 | Landing | Clicks "Get Started" | Routes to Auth |
| 2 | Auth | Fills email + password, submits | JWT issued, redirect to Dashboard |
| 3 | Dashboard | Views past conversations | Loads chat history from DB |
| 4 | Ask | Types question, presses Send | POST /rag/ask called |
| 5 | Answer | Reads response | Shows answer + collapsible source cards |

---

## 3. RAG Pipeline

```
┌─────────────┐    ┌─────────────┐    ┌──────────────────────┐    ┌──────────────┐
│  INGESTION  │───▶│  CHUNKING   │───▶│  EMBEDDINGS          │───▶│  VECTOR DB   │
│             │    │             │    │                      │    │              │
│ Load .json  │    │ 500 tokens  │    │ text-embedding-      │    │ ChromaDB     │
│ / .md files │    │ 50 overlap  │    │ 3-small (OpenAI)     │    │ persistent   │
│ from disk   │    │ LangChain   │    │ 1536-dim vectors     │    │ collection   │
│             │    │ splitter    │    │                      │    │              │
└─────────────┘    └─────────────┘    └──────────────────────┘    └──────┬───────┘
                                                                          │
                    ┌─────────────────────────────────────────────────────┘
                    │  (Query Time)
                    ▼
┌─────────────┐    ┌─────────────┐    ┌──────────────────────┐    ┌──────────────┐
│  ANSWER +   │◀───│  LLM        │◀───│  PROMPT ASSEMBLY     │◀───│  RETRIEVAL   │
│  SOURCES    │    │             │    │                      │    │              │
│             │    │ GPT-4o-mini │    │ System prompt +      │    │ Cosine sim   │
│ JSON shape  │    │ or GPT-4o   │    │ retrieved context +  │    │ top_k = 5    │
│ (see §5)    │    │ max 1024 t  │    │ user question        │    │ chunks       │
│             │    │             │    │                      │    │              │
└─────────────┘    └─────────────┘    └──────────────────────┘    └──────────────┘
```

### Pipeline Stage Details

| Stage | Tool / Library | Config |
|-------|---------------|--------|
| Ingestion | Python `os.walk` + `json`/`markdown` | Loads all files in `backend/data/docs/` |
| Chunking | LangChain `RecursiveCharacterTextSplitter` | chunk_size=500, chunk_overlap=50 |
| Embeddings | OpenAI `text-embedding-3-small` | 1536 dimensions |
| Vector DB | ChromaDB (local persistent) | Collection: `rag_copilot_docs` |
| Retrieval | ChromaDB `.query()` | top_k=5, metric=cosine |
| Prompt | LangChain `ChatPromptTemplate` | System + HumanMessage |
| LLM | OpenAI `gpt-4o-mini` | temperature=0.2, max_tokens=1024 |
| Output | Pydantic response model | Structured JSON |

---

## 4. Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11, FastAPI |
| **Vector DB** | ChromaDB (local) |
| **Embeddings** | OpenAI text-embedding-3-small |
| **LLM** | OpenAI gpt-4o-mini |
| **Auth** | JWT (python-jose), bcrypt |
| **Frontend** | React 18 + Vite + TypeScript |
| **HTTP Client** | Axios |
| **Styling** | Tailwind CSS |
| **Dev DB** | SQLite (via SQLAlchemy) for users/history |
| **Env Mgmt** | python-dotenv |

---

## 5. Dataset Decision

**Dataset: SaaS Product Help-Center (Fictional "CloudDesk" app)**

- **20–50 short documents** stored in `backend/data/docs/`
- Format: **JSON** (structured) + **Markdown** (narrative articles)
- Topics covered:
  - Account & billing FAQs
  - Feature how-tos (integrations, notifications, dashboards)
  - Troubleshooting guides
  - API usage examples
  - Onboarding steps

File naming convention: `doc_{id:03d}_{slug}.json` or `.md`

---

## 6. Project Folder Structure

```
rag-copilot/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py          # /auth/* routes
│   │   │   └── rag.py           # /rag/* routes
│   │   ├── core/
│   │   │   ├── config.py        # env settings
│   │   │   ├── security.py      # JWT helpers
│   │   │   └── embeddings.py    # embedding client
│   │   ├── services/
│   │   │   ├── rag_service.py   # ingest / retrieve / ask
│   │   │   └── auth_service.py  # signup / login logic
│   │   └── main.py              # FastAPI app entry
│   ├── data/
│   │   └── docs/                # 20-50 source documents
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── pages/
│       ├── components/
│       └── api/
├── docs/
│   ├── architecture.md          # this file
│   ├── api_contract.md          # endpoint specs
│   └── rag_pipeline.md          # pipeline deep-dive
└── README.md
```
