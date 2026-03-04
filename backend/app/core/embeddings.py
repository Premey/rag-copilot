"""
Embedding utilities using sentence-transformers (all-MiniLM-L6-v2).
Free, runs fully locally — no API key required.
384-dimensional vectors.
"""
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import settings


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """Load and cache the embedding model (downloaded once, then cached)."""
    return SentenceTransformer(settings.EMBEDDING_MODEL)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of text strings.
    Returns a list of float vectors (one per text).
    """
    model = get_embedding_model()
    embeddings = model.encode(texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
    return embeddings.tolist()


def embed_query(text: str) -> list[float]:
    """Generate embedding for a single query string."""
    return embed_texts([text])[0]
