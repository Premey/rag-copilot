"""
RAG API routes:
  POST /rag/ingest   — rebuild the vector index
  POST /rag/retrieve — debug retrieval (no LLM)
  POST /rag/ask      — question → answer + sources (retrieval + LLM)
  GET  /rag/metrics  — observability counters
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.metrics import metrics
from app.models.user import User
from app.schemas.rag import (
    AskRequest,
    AskResponse,
    IngestRequest,
    IngestResponse,
    RetrieveRequest,
    RetrieveResponse,
)
from app.services import rag_service

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
def ingest(
    req: IngestRequest,
    current_user: User = Depends(get_current_user),
):
    """Rebuild the vector index (embedding + BM25) from disk documents."""
    result = rag_service.ingest(force_rebuild=req.force_rebuild)
    return IngestResponse(
        status="success",
        docs_processed=result["docs_processed"],
        chunks_created=result["chunks_created"],
        collection=result.get("collection", "rag_copilot_docs"),
        duration_seconds=result["duration_seconds"],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve(
    req: RetrieveRequest,
    current_user: User = Depends(get_current_user),
):
    """Hybrid retrieve top-k chunks (embedding + BM25). No LLM."""
    results = rag_service.retrieve(req.question, top_k=req.top_k)
    return RetrieveResponse(
        question=req.question,
        top_k=req.top_k,
        results=results,
        collection="rag_copilot_docs",
        trace_id=f"trc_{uuid.uuid4().hex[:12]}",
    )


@router.post("/ask", response_model=AskResponse)
def ask(
    req: AskRequest,
    current_user: User = Depends(get_current_user),
):
    """Answer a question using hybrid retrieval + guardrails + LLM."""
    result = rag_service.ask(
        question=req.question,
        top_k=req.top_k,
        conversation_id=req.conversation_id,
    )
    return AskResponse(**result)


@router.get("/metrics", tags=["Observability"])
def get_metrics():
    """Return RAG observability counters: query counts, rates, latencies."""
    return metrics.snapshot()
