"""
Pure-Python BM25 (Okapi BM25) implementation.
No external dependencies beyond Python stdlib + numpy.
"""
import math
import re
from collections import Counter

import numpy as np

# ─── Tokenizer ────────────────────────────────────────────────────────────────

_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "i", "me", "my", "we", "our", "you", "your", "he", "him", "his",
    "she", "her", "it", "its", "they", "them", "their", "this", "that",
    "these", "those", "what", "which", "who", "whom", "when", "where",
    "why", "how", "not", "no", "nor", "and", "or", "but", "if", "then",
    "so", "as", "at", "by", "for", "in", "of", "on", "to", "up", "with",
    "from", "into", "about", "between", "through", "during", "before",
    "after", "above", "below", "all", "each", "every", "both", "few",
    "more", "most", "other", "some", "such", "only", "very",
})


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, remove stop words."""
    tokens = re.findall(r"\b[a-z0-9]+\b", text.lower())
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]


# ─── BM25 Index ──────────────────────────────────────────────────────────────

class BM25Index:
    """Okapi BM25 index for keyword-based retrieval."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size: int = 0
        self.avg_dl: float = 0.0
        self.doc_freqs: dict[str, int] = {}      # term → # docs containing it
        self.doc_lens: list[int] = []             # length of each doc
        self.term_freqs: list[dict[str, int]] = []  # per-doc term frequencies
        self.idf: dict[str, float] = {}

    def fit(self, documents: list[str]) -> "BM25Index":
        """Build the BM25 index from a list of document strings."""
        self.corpus_size = len(documents)
        self.doc_freqs = {}
        self.doc_lens = []
        self.term_freqs = []

        for doc in documents:
            tokens = _tokenize(doc)
            self.doc_lens.append(len(tokens))
            tf = Counter(tokens)
            self.term_freqs.append(dict(tf))
            # Count document frequency for each unique term
            for term in tf:
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1

        self.avg_dl = sum(self.doc_lens) / max(self.corpus_size, 1)

        # Pre-compute IDF for all terms
        self.idf = {}
        for term, df in self.doc_freqs.items():
            self.idf[term] = math.log(
                (self.corpus_size - df + 0.5) / (df + 0.5) + 1.0
            )

        return self

    def query(self, question: str, top_k: int = 5) -> list[tuple[int, float]]:
        """
        Score all documents against the query.
        Returns list of (doc_index, score) sorted by score descending, top-k only.
        """
        q_tokens = _tokenize(question)
        if not q_tokens:
            return []

        scores = np.zeros(self.corpus_size, dtype=np.float64)

        for term in q_tokens:
            if term not in self.idf:
                continue
            idf = self.idf[term]
            for i in range(self.corpus_size):
                tf = self.term_freqs[i].get(term, 0)
                if tf == 0:
                    continue
                dl = self.doc_lens[i]
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * dl / self.avg_dl)
                scores[i] += idf * numerator / denominator

        # Get top-k
        k = min(top_k, self.corpus_size)
        if k == 0:
            return []
        top_indices = np.argpartition(scores, -k)[-k:]
        top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

        return [(int(idx), float(scores[idx])) for idx in top_indices if scores[idx] > 0]
