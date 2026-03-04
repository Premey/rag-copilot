"""
Test suite for auth endpoints.
Uses an in-memory SQLite database so tests are isolated and fast.
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app

# ─── In-memory test DB ────────────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite:///./test_clouddesk.db"

test_engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    """Create all tables before each test, drop after."""
    from app.models import user  # noqa: F401 — registers models with Base
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ─── Test Data ────────────────────────────────────────────────────────────────
USER_PAYLOAD = {
    "email": "test@example.com",
    "password": "Test1234!",
    "full_name": "Test User",
}


# ─── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_signup_success(client: AsyncClient):
    response = await client.post("/auth/signup", json=USER_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == USER_PAYLOAD["email"]
    assert data["full_name"] == USER_PAYLOAD["full_name"]
    assert "user_id" in data
    assert "password_hash" not in data  # never leak password hash


@pytest.mark.asyncio
async def test_signup_duplicate_email(client: AsyncClient):
    await client.post("/auth/signup", json=USER_PAYLOAD)
    response = await client.post("/auth/signup", json=USER_PAYLOAD)
    assert response.status_code == 409
    assert "already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_signup_weak_password(client: AsyncClient):
    payload = {**USER_PAYLOAD, "password": "short"}
    response = await client.post("/auth/signup", json=payload)
    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_signup_invalid_email(client: AsyncClient):
    payload = {**USER_PAYLOAD, "email": "not-an-email"}
    response = await client.post("/auth/signup", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/auth/signup", json=USER_PAYLOAD)
    response = await client.post(
        "/auth/login",
        json={"email": USER_PAYLOAD["email"], "password": USER_PAYLOAD["password"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    assert data["user"]["email"] == USER_PAYLOAD["email"]


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/auth/signup", json=USER_PAYLOAD)
    response = await client.post(
        "/auth/login",
        json={"email": USER_PAYLOAD["email"], "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert "Invalid" in response.json()["detail"]


@pytest.mark.asyncio
async def test_me_authenticated(client: AsyncClient):
    # signup then login
    await client.post("/auth/signup", json=USER_PAYLOAD)
    login_resp = await client.post(
        "/auth/login",
        json={"email": USER_PAYLOAD["email"], "password": USER_PAYLOAD["password"]},
    )
    token = login_resp.json()["access_token"]

    # call /auth/me with token
    response = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == USER_PAYLOAD["email"]
    assert data["full_name"] == USER_PAYLOAD["full_name"]
    assert "user_id" in data


@pytest.mark.asyncio
async def test_me_unauthenticated(client: AsyncClient):
    response = await client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_invalid_token(client: AsyncClient):
    response = await client.get(
        "/auth/me", headers={"Authorization": "Bearer invalidtoken.abc.xyz"}
    )
    assert response.status_code == 401
