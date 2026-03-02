# RAG Copilot — API Contract

> **Base URL:** `http://localhost:8000`  
> **Auth:** Bearer JWT token in `Authorization` header (except `/auth/*` and `/health`)  
> **Content-Type:** `application/json`

---

## GET /health

**Purpose:** Verify the service is alive.  
**Auth Required:** No

### Request
```
GET /health
```

### Response `200 OK`
```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2026-03-02T14:20:00Z"
}
```

---

## POST /auth/signup

**Purpose:** Register a new user account.  
**Auth Required:** No

### Request Body
```json
{
  "email": "user@example.com",
  "password": "Str0ngPass!",
  "full_name": "Jane Doe"
}
```

### Response `201 Created`
```json
{
  "user_id": "usr_a1b2c3d4",
  "email": "user@example.com",
  "full_name": "Jane Doe",
  "created_at": "2026-03-02T14:20:00Z"
}
```

### Error Responses
```json
// 409 Conflict — email already exists
{
  "detail": "Email already registered"
}

// 422 Unprocessable Entity — validation error
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "Password must be at least 8 characters",
      "type": "value_error"
    }
  ]
}
```

---

## POST /auth/login

**Purpose:** Authenticate user and receive a JWT access token.  
**Auth Required:** No

### Request Body
```json
{
  "email": "user@example.com",
  "password": "Str0ngPass!"
}
```

### Response `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "user_id": "usr_a1b2c3d4",
    "email": "user@example.com",
    "full_name": "Jane Doe"
  }
}
```

### Error Responses
```json
// 401 Unauthorized
{
  "detail": "Invalid email or password"
}
```

---

## POST /rag/ingest

**Purpose:** Rebuild the vector index from all documents in `backend/data/docs/`.  
**Auth Required:** Yes (admin-level token recommended)

### Request Body
```json
{
  "force_rebuild": true
}
```

### Response `200 OK`
```json
{
  "status": "success",
  "docs_processed": 42,
  "chunks_created": 318,
  "collection": "rag_copilot_docs",
  "duration_seconds": 14.7,
  "timestamp": "2026-03-02T14:20:00Z"
}
```

### Error Responses
```json
// 500 Internal Server Error
{
  "detail": "Ingestion failed: OpenAI API error — rate limit exceeded"
}
```

---

## POST /rag/ask

**Purpose:** Answer a user question using retrieval-augmented generation.  
**Auth Required:** Yes

### Request Body
```json
{
  "question": "How do I reset my CloudDesk API key?",
  "top_k": 5,
  "conversation_id": "conv_xyz789"
}
```
> `top_k` is optional (default: 5). `conversation_id` is optional (links answer to a chat session).

### Response `200 OK` — Success
```json
{
  "answer": "To reset your CloudDesk API key, navigate to Settings → Developer → API Keys. Click the 'Regenerate' button next to your existing key. Note that your old key will be invalidated immediately.",
  "sources": [
    {
      "chunk_id": "chunk_doc012_02",
      "doc_id": "doc_012",
      "title": "Managing API Keys in CloudDesk",
      "chunk_text": "Navigate to Settings → Developer → API Keys. Click 'Regenerate' to create a new key. The old key is invalidated immediately upon regeneration.",
      "score": 0.923
    },
    {
      "chunk_id": "chunk_doc008_05",
      "doc_id": "doc_008",
      "title": "CloudDesk Security FAQ",
      "chunk_text": "For security best practices, rotate your API keys every 90 days. Revoked keys cannot be recovered.",
      "score": 0.781
    }
  ],
  "status": "ok",
  "trace_id": "trc_3f8a9b1c2d4e",
  "question": "How do I reset my CloudDesk API key?",
  "conversation_id": "conv_xyz789",
  "model_used": "gpt-4o-mini",
  "latency_ms": 1240
}
```

### Response `200 OK` — Low Context (no relevant docs found)
```json
{
  "answer": "I don't have enough relevant information in my knowledge base to answer this question confidently. Please try rephrasing or contact support.",
  "sources": [],
  "status": "low_context",
  "trace_id": "trc_9z1x2y3w4v",
  "question": "Who won the 2026 World Cup?",
  "conversation_id": "conv_xyz789",
  "model_used": "gpt-4o-mini",
  "latency_ms": 430
}
```

### Error Responses
```json
// 401 Unauthorized
{
  "detail": "Not authenticated"
}
// 500 Internal Server Error
{
  "detail": "LLM service unavailable"
}
```

---

## POST /rag/retrieve

**Purpose:** Debug endpoint — retrieve top-k chunks for a query WITHOUT invoking the LLM. Useful for tuning retrieval quality.  
**Auth Required:** Yes

### Request Body
```json
{
  "question": "How do I reset my CloudDesk API key?",
  "top_k": 5
}
```

### Response `200 OK`
```json
{
  "question": "How do I reset my CloudDesk API key?",
  "top_k": 5,
  "results": [
    {
      "chunk_id": "chunk_doc012_02",
      "doc_id": "doc_012",
      "title": "Managing API Keys in CloudDesk",
      "chunk_text": "Navigate to Settings → Developer → API Keys. Click 'Regenerate' to create a new key. The old key is invalidated immediately upon regeneration.",
      "score": 0.923
    },
    {
      "chunk_id": "chunk_doc008_05",
      "doc_id": "doc_008",
      "title": "CloudDesk Security FAQ",
      "chunk_text": "For security best practices, rotate your API keys every 90 days. Revoked keys cannot be recovered.",
      "score": 0.781
    },
    {
      "chunk_id": "chunk_doc007_01",
      "doc_id": "doc_007",
      "title": "CloudDesk Developer Guide",
      "chunk_text": "API authentication uses Bearer tokens. Generate keys from the Settings panel. Each workspace supports up to 10 active API keys.",
      "score": 0.712
    }
  ],
  "collection": "rag_copilot_docs",
  "trace_id": "trc_debug_0a1b2c"
}
```

---

## Response Shape Summary — `/rag/ask`

```
{
  answer:          string          — LLM-generated response text
  sources:         Source[]        — list of grounding chunks
    └── chunk_id:  string          — unique chunk identifier
    └── doc_id:    string          — parent document id
    └── title:     string          — document title
    └── chunk_text: string         — the exact retrieved text
    └── score:     float (0–1)     — cosine similarity score
  status:          "ok" | "low_context"
  trace_id:        string          — for debugging / logging
  question:        string          — echo of input question
  conversation_id: string | null   — session linkage
  model_used:      string          — which LLM was used
  latency_ms:      int             — end-to-end response time
}
```

---

## API Endpoint Summary Table

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/health` | No | Service liveness check |
| POST | `/auth/signup` | No | Register new user |
| POST | `/auth/login` | No | Login + get JWT |
| POST | `/rag/ingest` | Yes | Rebuild vector index |
| POST | `/rag/ask` | Yes | Question → Answer + Sources |
| POST | `/rag/retrieve` | Yes | Debug: retrieval only (no LLM) |
