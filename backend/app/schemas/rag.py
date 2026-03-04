"""
Pydantic schemas for RAG ingest, retrieve, and ask endpoints.
"""

from pydantic import BaseModel, field_validator

# ─── Ingest ───────────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    force_rebuild: bool = True


class IngestResponse(BaseModel):
    status: str
    docs_processed: int
    chunks_created: int
    collection: str
    duration_seconds: float
    timestamp: str


# ─── Retrieve ─────────────────────────────────────────────────────────────────

class RetrieveRequest(BaseModel):
    question: str
    top_k: int = 5

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Question must not be empty")
        return v.strip()

    @field_validator("top_k")
    @classmethod
    def top_k_range(cls, v: int) -> int:
        if v < 1 or v > 20:
            raise ValueError("top_k must be between 1 and 20")
        return v


class ChunkResult(BaseModel):
    chunk_id: str
    doc_id: str
    title: str
    chunk_text: str
    score: float


class RetrieveResponse(BaseModel):
    question: str
    top_k: int
    results: list[ChunkResult]
    collection: str
    trace_id: str


# ─── Ask (Retrieval + LLM) ───────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str
    top_k: int = 5
    conversation_id: str | None = None

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Question must not be empty")
        return v.strip()

    @field_validator("top_k")
    @classmethod
    def top_k_range(cls, v: int) -> int:
        if v < 1 or v > 20:
            raise ValueError("top_k must be between 1 and 20")
        return v


class AskResponse(BaseModel):
    answer: str
    sources: list[ChunkResult]
    status: str  # "ok" | "low_context"
    trace_id: str
    question: str
    conversation_id: str | None = None
    model_used: str
    latency_ms: int
