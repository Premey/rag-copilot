"""
Metrics store — simple in-memory counters for /rag/metrics.
Thread-safe via threading.Lock.
"""
import threading
from datetime import datetime, timezone
from typing import Dict, Any


class MetricsStore:
    """In-memory counters for RAG observability."""

    def __init__(self):
        self._lock = threading.Lock()
        self._counters = {
            "total_queries": 0,
            "ok_count": 0,
            "low_context_count": 0,
            "error_count": 0,
            "total_latency_ms": 0,
            "total_top_score": 0.0,
            "ingest_count": 0,
        }
        self._started_at = datetime.now(timezone.utc).isoformat()

    def record_query(self, status: str, latency_ms: int, top_score: float):
        with self._lock:
            self._counters["total_queries"] += 1
            self._counters["total_latency_ms"] += latency_ms
            self._counters["total_top_score"] += top_score
            if status == "ok":
                self._counters["ok_count"] += 1
            elif status == "low_context":
                self._counters["low_context_count"] += 1
            else:
                self._counters["error_count"] += 1

    def record_ingest(self):
        with self._lock:
            self._counters["ingest_count"] += 1

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            total = self._counters["total_queries"]
            return {
                "total_queries": total,
                "ok_count": self._counters["ok_count"],
                "low_context_count": self._counters["low_context_count"],
                "error_count": self._counters["error_count"],
                "avg_latency_ms": round(self._counters["total_latency_ms"] / max(total, 1)),
                "avg_top_score": round(self._counters["total_top_score"] / max(total, 1), 4),
                "answerable_rate": round(self._counters["ok_count"] / max(total, 1), 4),
                "refusal_rate": round(self._counters["low_context_count"] / max(total, 1), 4),
                "ingest_count": self._counters["ingest_count"],
                "started_at": self._started_at,
            }


# Singleton
metrics = MetricsStore()
