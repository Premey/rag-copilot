"""
LLM utility — Google Gemini Flash (free tier).

Provides a `generate_answer()` function that sends a prompt to the LLM
and returns the generated text.

To use: set GOOGLE_API_KEY in .env (free at https://aistudio.google.com/apikey)
"""
import logging
from typing import Optional

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger("rag-copilot")

# Module-level Gemini client (lazy-initialized)
_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    """Return (or create) the Gemini API client."""
    global _client
    if _client is None:
        if not settings.GOOGLE_API_KEY:
            raise RuntimeError(
                "GOOGLE_API_KEY is not set. "
                "Get a free key at https://aistudio.google.com/apikey "
                "and add it to your .env file."
            )
        _client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        logger.info("Gemini client created for model: %s", settings.LLM_MODEL)
    return _client


# ─── System prompt for RAG grounded answers ───────────────────────────────────

SYSTEM_PROMPT = """You are a helpful assistant for CloudDesk, a SaaS customer support platform.
Answer the user's question using ONLY the context provided below.
If the context does not contain enough information to answer confidently, say:
"I don't have enough information in my knowledge base to answer this question."
Do NOT make up facts. Do NOT use information outside the provided context.
Be concise and cite which part of the context you used."""


def generate_answer(
    question: str,
    context: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Send a prompt (system + context + question) to Gemini and return the answer text.
    """
    client = _get_client()

    prompt = f"""Context:
---
{context}
---

Question: {question}

Answer concisely based only on the context above:"""

    response = client.models.generate_content(
        model=settings.LLM_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=temperature if temperature is not None else settings.LLM_TEMPERATURE,
            max_output_tokens=max_tokens or settings.LLM_MAX_TOKENS,
        ),
    )
    return response.text.strip()
