from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    SECRET_KEY: str = "dev-secret-key-replace-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    DATABASE_URL: str = "sqlite:///./clouddesk.db"

    # CORS
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    # ─── RAG Pipeline ─────────────────────────────────────────────
    DOCS_PATH: str = "./data/docs"
    VECTOR_DB_PATH: str = "./.chroma"
    CHROMA_COLLECTION: str = "rag_copilot_docs"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    RETRIEVE_TOP_K: int = 5
    LOW_CONTEXT_THRESHOLD: float = 0.50
    MIN_RELEVANT_CHUNKS: int = 1       # guardrail: need at least N good chunks
    BM25_WEIGHT: float = 0.3           # hybrid: 30% BM25, 70% embedding

    # ─── LLM ──────────────────────────────────────────────────────
    GOOGLE_API_KEY: str = ""
    LLM_MODEL: str = "gemini-2.0-flash"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 1024

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
