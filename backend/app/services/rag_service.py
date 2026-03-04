"""
RAG Service — ingestion and retrieval pipeline using a pure-Python vector store.

Uses numpy for cosine similarity + pickle for disk persistence.
No C++ compiler needed — works on any Python environment.

Ingestion Phase:
  load_docs → chunk_docs → embed → save index to disk

Retrieval Phase:
  embed_query → cosine similarity → top-k ChunkResult list
"""
import json
import logging
import os
import pickle
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.core.embeddings import embed_query as _embed_query
from app.core.embeddings import embed_texts
from app.schemas.rag import ChunkResult

logger = logging.getLogger("rag-copilot")


def _index_path() -> str:
    """Return the path where the vector index is persisted (computed dynamically)."""
    return os.path.join(settings.VECTOR_DB_PATH, "rag_index.pkl")


# ─── Vector Index dataclass ───────────────────────────────────────────────────

@dataclass
class VectorIndex:
    """Simple in-memory vector index persisted to disk via pickle."""
    chunk_ids: list[str] = field(default_factory=list)
    doc_ids: list[str] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    vectors: np.ndarray | None = None  # shape: (N, D)

    def size(self) -> int:
        return len(self.chunk_ids)


def _save_index(index: VectorIndex) -> None:
    """Persist the index to disk."""
    os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)
    path = _index_path()
    with open(path, "wb") as f:
        pickle.dump(index, f, protocol=pickle.HIGHEST_PROTOCOL)
    logger.info("Index saved to %s (%d chunks)", path, index.size())


def _load_index() -> VectorIndex | None:
    """Load index from disk. Returns None if not found."""
    path = _index_path()
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


# ─── Phase 1: Load Documents ─────────────────────────────────────────────────

def load_docs(docs_path: str) -> list[dict[str, str]]:
    """
    Read all .json and .md files from docs_path.
    Returns list of dicts: {doc_id, title, content}
    """
    docs = []
    p = Path(docs_path)
    if not p.exists():
        raise FileNotFoundError(f"Docs directory not found: {docs_path}")

    for f in sorted(p.iterdir()):
        if f.suffix == ".json":
            try:
                raw = json.loads(f.read_text(encoding="utf-8"))
                docs.append({
                    "doc_id": raw.get("doc_id", f.stem),
                    "title": raw.get("title", f.stem),
                    "content": raw.get("content", ""),
                })
            except Exception as e:
                logger.warning("Skipping %s: %s", f.name, e)

        elif f.suffix == ".md":
            text = f.read_text(encoding="utf-8")
            # Derive title from first # heading, fallback to filename
            title = " ".join(f.stem.split("_")[2:]).title() if "_" in f.stem else f.stem
            for line in text.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
            # doc_id from stem prefix e.g. doc_011_notifications → doc_011
            parts = f.stem.split("_")
            doc_id = "_".join(parts[:2]) if len(parts) >= 2 else f.stem
            docs.append({"doc_id": doc_id, "title": title, "content": text})

    logger.info("Loaded %d documents from %s", len(docs), docs_path)
    return docs


# ─── Phase 2: Chunk Documents ────────────────────────────────────────────────

def chunk_docs(docs: list[dict[str, str]]) -> list[dict[str, Any]]:
    """
    Split each document into overlapping chunks.
    Returns list of: {chunk_id, doc_id, title, chunk_text}
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    for doc in docs:
        if not doc["content"].strip():
            continue
        parts = splitter.split_text(doc["content"])
        for i, part in enumerate(parts):
            chunks.append({
                "chunk_id": f"{doc['doc_id']}_chunk_{i:03d}",
                "doc_id": doc["doc_id"],
                "title": doc["title"],
                "chunk_text": part.strip(),
            })
    logger.info("Created %d chunks from %d docs", len(chunks), len(docs))
    return chunks


# ─── Phase 3+4: Embed + Persist ──────────────────────────────────────────────

def ingest(force_rebuild: bool = True) -> dict[str, Any]:
    """
    Full ingestion pipeline: load → chunk → embed → build BM25 → save index.
    """
    from app.core.bm25 import BM25Index
    from app.core.metrics import metrics

    start = time.perf_counter()
    docs = load_docs(settings.DOCS_PATH)
    chunks = chunk_docs(docs)

    if not chunks:
        return {
            "docs_processed": len(docs),
            "chunks_created": 0,
            "collection": settings.CHROMA_COLLECTION,
            "duration_seconds": round(time.perf_counter() - start, 2),
        }

    texts = [c["chunk_text"] for c in chunks]

    # Embed all chunks
    logger.info("Generating embeddings for %d chunks...", len(texts))
    raw_vectors = embed_texts(texts)
    vectors = np.array(raw_vectors, dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-9, norms)
    vectors = vectors / norms

    # Build BM25 index
    logger.info("Building BM25 index...")
    bm25 = BM25Index()
    bm25.fit(texts)

    # Build and save combined index
    index = VectorIndex(
        chunk_ids=[c["chunk_id"] for c in chunks],
        doc_ids=[c["doc_id"] for c in chunks],
        titles=[c["title"] for c in chunks],
        texts=texts,
        vectors=vectors,
    )
    _save_index(index)

    # Save BM25 index separately
    bm25_path = os.path.join(settings.VECTOR_DB_PATH, "bm25_index.pkl")
    os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)
    with open(bm25_path, "wb") as f:
        pickle.dump(bm25, f, protocol=pickle.HIGHEST_PROTOCOL)
    logger.info("BM25 index saved (%d docs)", bm25.corpus_size)

    metrics.record_ingest()
    duration = round(time.perf_counter() - start, 2)
    logger.info("Ingestion complete: %d docs, %d chunks, %.2fs", len(docs), len(chunks), duration)

    return {
        "docs_processed": len(docs),
        "chunks_created": len(chunks),
        "collection": settings.CHROMA_COLLECTION,
        "duration_seconds": duration,
    }


# ─── Load BM25 index ─────────────────────────────────────────────────────────

def _load_bm25():
    """Load BM25 index from disk. Returns None if not found."""
    bm25_path = os.path.join(settings.VECTOR_DB_PATH, "bm25_index.pkl")
    if not os.path.exists(bm25_path):
        return None
    with open(bm25_path, "rb") as f:
        return pickle.load(f)


# ─── Phase 5: Hybrid Retrieve (Embedding + BM25) ─────────────────────────────

def retrieve(question: str, top_k: int = None) -> list[ChunkResult]:
    """
    Hybrid retrieval: combine embedding cosine similarity and BM25 keyword scores.
    Final score = (1 - BM25_WEIGHT) * embedding_score + BM25_WEIGHT * bm25_score_normalized
    """
    k = top_k or settings.RETRIEVE_TOP_K
    index = _load_index()

    if index is None or index.size() == 0:
        return []

    # ── Embedding scores ──
    q_vec = np.array(_embed_query(question), dtype=np.float32)
    q_norm = np.linalg.norm(q_vec)
    if q_norm > 0:
        q_vec = q_vec / q_norm
    emb_scores = index.vectors @ q_vec  # shape: (N,)

    # ── BM25 scores ──
    bm25 = _load_bm25()
    bm25_scores = np.zeros(index.size(), dtype=np.float64)
    if bm25 is not None:
        bm25_results = bm25.query(question, top_k=index.size())
        for idx, score in bm25_results:
            if idx < index.size():
                bm25_scores[idx] = score

    # Normalize BM25 to [0, 1]
    bm25_max = bm25_scores.max() if bm25_scores.max() > 0 else 1.0
    bm25_norm = bm25_scores / bm25_max

    # ── Hybrid merge ──
    w = settings.BM25_WEIGHT
    hybrid_scores = (1 - w) * emb_scores + w * bm25_norm

    # Get top-k
    k = min(k, index.size())
    top_indices = np.argpartition(hybrid_scores, -k)[-k:]
    top_indices = top_indices[np.argsort(hybrid_scores[top_indices])[::-1]]

    results = []
    for idx in top_indices:
        score = float(hybrid_scores[idx])
        results.append(ChunkResult(
            chunk_id=index.chunk_ids[idx],
            doc_id=index.doc_ids[idx],
            title=index.titles[idx],
            chunk_text=index.texts[idx],
            score=round(score, 4),
        ))

    return results


# ─── Phase 6: Ask (Retrieve + Guardrails + LLM) ──────────────────────────────

def ask(question: str, top_k: int = None, conversation_id: str = None) -> dict[str, Any]:
    """
    Full RAG ask pipeline with guardrails:
      1. Hybrid retrieve (embedding + BM25)
      2. Filter by LOW_CONTEXT_THRESHOLD
      3. Guardrail: require MIN_RELEVANT_CHUNKS above threshold
      4. Build context → call LLM
      5. Record metrics
    """
    import uuid

    from app.core.llm import generate_answer
    from app.core.metrics import metrics

    start = time.perf_counter()
    k = top_k or settings.RETRIEVE_TOP_K
    trace_id = f"trc_{uuid.uuid4().hex[:12]}"

    # Step 1: Hybrid retrieve
    chunks = retrieve(question, top_k=k)

    # Step 2+3: Guardrails — filter + minimum chunk count
    relevant = [c for c in chunks if c.score >= settings.LOW_CONTEXT_THRESHOLD]
    top_score = relevant[0].score if relevant else (chunks[0].score if chunks else 0.0)

    if len(relevant) < settings.MIN_RELEVANT_CHUNKS:
        latency = round((time.perf_counter() - start) * 1000)
        logger.info(
            "GUARDRAIL: low_context | trace=%s q='%s' relevant=%d min=%d top_score=%.4f",
            trace_id, question[:60], len(relevant), settings.MIN_RELEVANT_CHUNKS, top_score,
        )
        metrics.record_query("low_context", latency, top_score)
        return {
            "answer": "I don't have enough relevant information in my knowledge base to answer this question confidently. Please try rephrasing or contact support.",
            "sources": [],
            "status": "low_context",
            "trace_id": trace_id,
            "question": question,
            "conversation_id": conversation_id,
            "model_used": settings.LLM_MODEL,
            "latency_ms": latency,
        }

    # Step 4: Build context + call LLM
    context_parts = []
    for i, chunk in enumerate(relevant):
        context_parts.append(f"[Source {i+1}: {chunk.title}]\n{chunk.chunk_text}")
    context = "\n\n".join(context_parts)

    logger.info(
        "LLM call | trace=%s q='%s' chunks=%d top_score=%.4f",
        trace_id, question[:60], len(relevant), top_score,
    )
    try:
        answer = generate_answer(question, context)
        status = "ok"
    except Exception as e:
        logger.error("LLM call failed | trace=%s error=%s", trace_id, e)
        answer = f"Error generating answer: {str(e)}"
        status = "error"

    latency = round((time.perf_counter() - start) * 1000)
    logger.info(
        "ASK complete | trace=%s status=%s latency=%dms scores=[%s]",
        trace_id, status, latency,
        ",".join(f"{c.score:.3f}" for c in relevant[:3]),
    )

    # Step 5: Record metrics
    metrics.record_query(status, latency, top_score)

    return {
        "answer": answer,
        "sources": relevant,
        "status": status,
        "trace_id": trace_id,
        "question": question,
        "conversation_id": conversation_id,
        "model_used": settings.LLM_MODEL,
        "latency_ms": latency,
    }


