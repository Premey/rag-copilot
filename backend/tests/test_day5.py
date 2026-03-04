"""
Day 5 tests: BM25 hybrid retrieval, guardrails, metrics, and eval harness.
"""
import os
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///./test_clouddesk_day5.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    from app.models import user  # noqa: F401
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db

    from app.core import config as cfg
    monkeypatch.setattr(cfg.settings, "VECTOR_DB_PATH", str(tmp_path / ".vectordb"))
    real_docs = os.path.join(os.path.dirname(__file__), "..", "data", "docs")
    monkeypatch.setattr(cfg.settings, "DOCS_PATH", os.path.abspath(real_docs))

    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


async def get_auth_token(client: AsyncClient) -> str:
    await client.post(
        "/auth/signup",
        json={"email": "day5@test.com", "password": "Test1234!", "full_name": "Day5"},
    )
    resp = await client.post(
        "/auth/login",
        json={"email": "day5@test.com", "password": "Test1234!"},
    )
    return resp.json()["access_token"]


async def do_ingest(client, token):
    await client.post(
        "/rag/ingest",
        json={"force_rebuild": True},
        headers={"Authorization": f"Bearer {token}"},
    )


# ─── BM25 Unit Tests ─────────────────────────────────────────────────────────

def test_bm25_basic():
    from app.core.bm25 import BM25Index
    docs = [
        "How to reset your API key in CloudDesk settings",
        "Billing plans and subscription pricing details",
        "Two-factor authentication setup guide",
    ]
    bm25 = BM25Index()
    bm25.fit(docs)
    results = bm25.query("API key reset", top_k=2)
    assert len(results) > 0
    # First result should be the API key doc
    assert results[0][0] == 0


def test_bm25_no_match():
    from app.core.bm25 import BM25Index
    bm25 = BM25Index()
    bm25.fit(["hello world", "foo bar"])
    results = bm25.query("quantum physics", top_k=2)
    # Should return empty or very low scores
    assert len(results) == 0 or results[0][1] < 0.1


# ─── Hybrid Retrieval Tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hybrid_retrieve_returns_results(client: AsyncClient):
    token = await get_auth_token(client)
    await do_ingest(client, token)
    resp = await client.post(
        "/rag/retrieve",
        json={"question": "API key reset", "top_k": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) > 0
    assert results[0]["score"] > 0.3


@pytest.mark.asyncio
async def test_hybrid_retrieve_keyword_boost(client: AsyncClient):
    """BM25 should boost results that contain exact query keywords."""
    token = await get_auth_token(client)
    await do_ingest(client, token)
    resp = await client.post(
        "/rag/retrieve",
        json={"question": "SLA response time critical", "top_k": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    results = resp.json()["results"]
    # SLA doc should appear in top results
    titles = [r["title"] for r in results]
    assert any("SLA" in t.upper() for t in titles), f"Expected SLA doc in {titles}"


# ─── Guardrails Tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_guardrail_min_chunks(client: AsyncClient):
    """When MIN_RELEVANT_CHUNKS = 2, a query with only 1 good chunk should refuse."""
    token = await get_auth_token(client)
    await do_ingest(client, token)

    from app.core import config as cfg
    original = cfg.settings.MIN_RELEVANT_CHUNKS
    cfg.settings.MIN_RELEVANT_CHUNKS = 99  # impossibly high

    with patch("app.core.llm.generate_answer", return_value="test"):
        resp = await client.post(
            "/rag/ask",
            json={"question": "How do I reset my API key?"},
            headers={"Authorization": f"Bearer {token}"},
        )

    cfg.settings.MIN_RELEVANT_CHUNKS = original
    assert resp.json()["status"] == "low_context"


# ─── Metrics Tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_metrics_endpoint(client: AsyncClient):
    resp = await client.get("/rag/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_queries" in data
    assert "ok_count" in data
    assert "low_context_count" in data
    assert "avg_latency_ms" in data
    assert "answerable_rate" in data
    assert "refusal_rate" in data
    assert "ingest_count" in data


@pytest.mark.asyncio
async def test_metrics_increment_on_ask(client: AsyncClient):
    """Metrics should increment after each /rag/ask call."""
    from app.core.metrics import metrics
    before = metrics.snapshot()["total_queries"]

    token = await get_auth_token(client)
    await do_ingest(client, token)
    with patch("app.core.llm.generate_answer", return_value="test answer"):
        await client.post(
            "/rag/ask",
            json={"question": "How do I enable 2FA?"},
            headers={"Authorization": f"Bearer {token}"},
        )

    after = metrics.snapshot()["total_queries"]
    assert after > before


# ─── Eval Set Validation ─────────────────────────────────────────────────────

def test_eval_json_valid():
    """eval.json should exist and contain 20 entries with required fields."""
    import json
    eval_path = os.path.join(os.path.dirname(__file__), "..", "data", "eval.json")
    with open(eval_path, encoding="utf-8") as f:
        data = json.load(f)

    entries = data["eval_set"]
    assert len(entries) == 20
    for e in entries:
        assert "id" in e
        assert "question" in e
        assert "answerable" in e
        assert isinstance(e["question"], str) and len(e["question"]) > 0
