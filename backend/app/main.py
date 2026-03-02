"""
FastAPI application entry point.

Features:
  - CORS for frontend origin
  - Logging middleware (method, path, status, latency)
  - GET /health
  - Auth routes: POST /auth/signup, POST /auth/login, GET /auth/me
  - RAG routes: POST /rag/ingest, POST /rag/retrieve
  - Auto-creates DB tables on startup
"""
import time
import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.api.auth import router as auth_router
from app.api.rag import router as rag_router

# ─── Logging Setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("rag-copilot")

# ─── App Instance ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="RAG Copilot API",
    description="Conversational AI grounded in your document knowledge base",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Logging Middleware ───────────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log method, path, status code, and latency for every request."""
    start = time.perf_counter()
    response = await call_next(request)
    latency_ms = round((time.perf_counter() - start) * 1000, 1)
    logger.info(
        "%s %s → %s  [%.1fms]",
        request.method,
        request.url.path,
        response.status_code,
        latency_ms,
    )
    return response

# ─── Startup: Create DB Tables ────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    # Import models so SQLAlchemy registers them with Base before create_all
    from app.models import user  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created / verified ✓")

# ─── Routes ───────────────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(rag_router, prefix="/rag", tags=["RAG"])


@app.get("/health", tags=["Health"])
def health():
    """Service liveness check — returns status: ok."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
