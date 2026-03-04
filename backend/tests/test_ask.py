"""
Test suite for /rag/ask endpoint (Day 4).

Tests are split into two categories:
  1. Unit tests that mock the LLM (fast, no API key needed)
  2. Integration tests that require GOOGLE_API_KEY (optional, skipped if no key)
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

# ─── Test DB setup ────────────────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite:///./test_clouddesk_ask.db"
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
    """Create tables, override DB, and patch paths for tests."""
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
        json={"email": "ask@test.com", "password": "Test1234!", "full_name": "Ask Tester"},
    )
    resp = await client.post(
        "/auth/login",
        json={"email": "ask@test.com", "password": "Test1234!"},
    )
    return resp.json()["access_token"]


async def do_ingest(client, token):
    await client.post(
        "/rag/ingest",
        json={"force_rebuild": True},
        headers={"Authorization": f"Bearer {token}"},
    )


# ─── Tests with Mocked LLM ───────────────────────────────────────────────────

MOCK_ANSWER = "To reset your API key, go to Settings → Developer → API Keys and click Regenerate."


@pytest.mark.asyncio
async def test_ask_returns_all_fields(client: AsyncClient):
    """Verify /rag/ask response shape: answer, sources, status, trace_id."""
    token = await get_auth_token(client)
    await do_ingest(client, token)

    with patch("app.core.llm.generate_answer", return_value=MOCK_ANSWER):
        resp = await client.post(
            "/rag/ask",
            json={"question": "How do I reset my API key?"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    # All required fields present
    assert "answer" in data
    assert "sources" in data
    assert "status" in data
    assert "trace_id" in data
    assert "question" in data
    assert "model_used" in data
    assert "latency_ms" in data
    # Status should be ok since we have relevant docs
    assert data["status"] == "ok"
    assert data["answer"] == MOCK_ANSWER
    assert len(data["sources"]) > 0
    assert data["sources"][0]["score"] > 0.3


@pytest.mark.asyncio
async def test_ask_low_context(client: AsyncClient):
    """Off-topic question should return status=low_context without hallucination."""
    token = await get_auth_token(client)
    await do_ingest(client, token)

    # Monkeypatch threshold to be very high so everything is "low context"
    from app.core import config as cfg
    original = cfg.settings.LOW_CONTEXT_THRESHOLD
    cfg.settings.LOW_CONTEXT_THRESHOLD = 0.99  # nothing passes this

    resp = await client.post(
        "/rag/ask",
        json={"question": "What is the weather in Tokyo?"},
        headers={"Authorization": f"Bearer {token}"},
    )

    cfg.settings.LOW_CONTEXT_THRESHOLD = original  # restore

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "low_context"
    assert data["sources"] == []
    assert "don't have enough" in data["answer"].lower() or "not enough" in data["answer"].lower()


@pytest.mark.asyncio
async def test_ask_requires_auth(client: AsyncClient):
    resp = await client.post(
        "/rag/ask",
        json={"question": "test question"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ask_empty_question(client: AsyncClient):
    token = await get_auth_token(client)
    resp = await client.post(
        "/rag/ask",
        json={"question": "   "},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ask_sources_have_required_fields(client: AsyncClient):
    token = await get_auth_token(client)
    await do_ingest(client, token)

    with patch("app.core.llm.generate_answer", return_value=MOCK_ANSWER):
        resp = await client.post(
            "/rag/ask",
            json={"question": "How do I set up Slack integration?"},
            headers={"Authorization": f"Bearer {token}"},
        )

    data = resp.json()
    assert data["status"] == "ok"
    for src in data["sources"]:
        assert "chunk_id" in src
        assert "doc_id" in src
        assert "title" in src
        assert "chunk_text" in src
        assert "score" in src


@pytest.mark.asyncio
async def test_ask_conversation_id_round_trip(client: AsyncClient):
    """conversation_id should be echoed back in response."""
    token = await get_auth_token(client)
    await do_ingest(client, token)

    with patch("app.core.llm.generate_answer", return_value=MOCK_ANSWER):
        resp = await client.post(
            "/rag/ask",
            json={"question": "billing plans", "conversation_id": "conv_test123"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.json()["conversation_id"] == "conv_test123"


@pytest.mark.asyncio
async def test_ask_trace_id_unique(client: AsyncClient):
    """Each call should return a unique trace_id."""
    token = await get_auth_token(client)
    await do_ingest(client, token)

    trace_ids = []
    with patch("app.core.llm.generate_answer", return_value=MOCK_ANSWER):
        for _ in range(3):
            resp = await client.post(
                "/rag/ask",
                json={"question": "API rate limits"},
                headers={"Authorization": f"Bearer {token}"},
            )
            trace_ids.append(resp.json()["trace_id"])

    assert len(set(trace_ids)) == 3, "Each trace_id should be unique"
