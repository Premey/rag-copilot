"""
Test suite for RAG pipeline: /rag/ingest and /rag/retrieve.
Uses an in-memory test DB for auth + real ChromaDB on a temp path.
"""
import os
import shutil
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db

# ─── In-memory / test DB setup ────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite:///./test_clouddesk_rag.db"
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
    """Create tables, override DB dependency, and patch paths for tests."""
    from app.models import user  # noqa: F401
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db

    from app.core import config as cfg
    # Patch vector DB to temp dir so tests don't pollute production .chroma
    monkeypatch.setattr(cfg.settings, "VECTOR_DB_PATH", str(tmp_path / ".vectordb"))
    # Patch DOCS_PATH to the actual docs directory (absolute path)
    real_docs = os.path.join(os.path.dirname(__file__), "..", "data", "docs")
    real_docs = os.path.abspath(real_docs)
    monkeypatch.setattr(cfg.settings, "DOCS_PATH", real_docs)

    yield

    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ─── Helper: signup + login, return token ─────────────────────────────────────
async def get_auth_token(client: AsyncClient) -> str:
    await client.post(
        "/auth/signup",
        json={"email": "rag@test.com", "password": "Test1234!", "full_name": "RAG Tester"},
    )
    resp = await client.post(
        "/auth/login",
        json={"email": "rag@test.com", "password": "Test1234!"},
    )
    return resp.json()["access_token"]


# ─── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingest_returns_success(client: AsyncClient):
    token = await get_auth_token(client)
    resp = await client.post(
        "/rag/ingest",
        json={"force_rebuild": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["docs_processed"] > 0
    assert data["chunks_created"] > 0
    assert "duration_seconds" in data


@pytest.mark.asyncio
async def test_ingest_requires_auth(client: AsyncClient):
    resp = await client.post("/rag/ingest", json={"force_rebuild": True})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_retrieve_after_ingest(client: AsyncClient):
    token = await get_auth_token(client)
    # Ingest first
    await client.post(
        "/rag/ingest",
        json={"force_rebuild": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Now retrieve
    resp = await client.post(
        "/rag/retrieve",
        json={"question": "How do I reset my API key?", "top_k": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["question"] == "How do I reset my API key?"
    assert isinstance(data["results"], list)
    assert len(data["results"]) > 0
    # Top result should be relevant — score > 0.3
    assert data["results"][0]["score"] > 0.3
    assert "chunk_text" in data["results"][0]
    assert "title" in data["results"][0]
    assert "trace_id" in data


@pytest.mark.asyncio
async def test_retrieve_empty_collection(client: AsyncClient):
    """Retrieve without ingesting first should return empty results (not error)."""
    token = await get_auth_token(client)
    resp = await client.post(
        "/rag/retrieve",
        json={"question": "What is CloudDesk?", "top_k": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["results"] == []


@pytest.mark.asyncio
async def test_retrieve_empty_question(client: AsyncClient):
    token = await get_auth_token(client)
    resp = await client.post(
        "/rag/retrieve",
        json={"question": "   ", "top_k": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_retrieve_requires_auth(client: AsyncClient):
    resp = await client.post(
        "/rag/retrieve",
        json={"question": "test question", "top_k": 3},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_retrieve_results_sorted_by_score(client: AsyncClient):
    token = await get_auth_token(client)
    await client.post(
        "/rag/ingest",
        json={"force_rebuild": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.post(
        "/rag/retrieve",
        json={"question": "billing subscription pricing plans", "top_k": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    results = resp.json()["results"]
    if len(results) > 1:
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True), "Results should be sorted by score desc"
