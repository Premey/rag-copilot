"""
Evaluation harness — run all questions from eval.json through the RAG pipeline
and report metrics (no LLM needed, uses retrieval only).

Run: python -m scripts.run_eval
"""
import json
import sys
import os
import time

# Add the backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.services import rag_service


def run_eval():
    eval_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "eval.json")
    with open(eval_path, encoding="utf-8") as f:
        data = json.load(f)

    entries = data["eval_set"]
    print(f"=== RAG Evaluation Harness -- {len(entries)} questions ===\n")

    # Ensure index exists
    print("Ingesting docs...")
    result = rag_service.ingest(force_rebuild=True)
    print(f"Ingested {result['docs_processed']} docs -> {result['chunks_created']} chunks\n")

    ok_count = 0
    low_context_count = 0
    correct_doc_count = 0
    total_top_score = 0.0
    total_latency = 0.0
    results = []

    for entry in entries:
        qid = entry["id"]
        question = entry["question"]
        expected_doc = entry.get("expected_doc")
        answerable = entry["answerable"]

        start = time.perf_counter()
        chunks = rag_service.retrieve(question, top_k=5)
        latency = round((time.perf_counter() - start) * 1000, 1)

        top_score = chunks[0].score if chunks else 0.0
        top_doc = chunks[0].doc_id if chunks else None
        relevant = [c for c in chunks if c.score >= settings.LOW_CONTEXT_THRESHOLD]
        status = "ok" if len(relevant) >= settings.MIN_RELEVANT_CHUNKS else "low_context"

        # Check correctness
        doc_match = False
        if answerable and expected_doc and top_doc:
            doc_match = expected_doc in top_doc
            if doc_match:
                correct_doc_count += 1

        if status == "ok":
            ok_count += 1
        else:
            low_context_count += 1

        total_top_score += top_score
        total_latency += latency

        icon = "OK  " if (answerable and status == "ok") or (not answerable and status == "low_context") else "FAIL"
        doc_icon = "OK" if doc_match else ("--" if not answerable else "NO")
        print(f"  [{icon}] Q{qid:02d}: {question[:55]:55s} | status={status:11s} score={top_score:.4f} doc={doc_icon} {latency:.0f}ms")

        results.append({
            "id": qid, "question": question, "answerable": answerable,
            "status": status, "top_score": top_score, "top_doc": top_doc,
            "expected_doc": expected_doc, "doc_match": doc_match,
            "correct_classification": (answerable and status == "ok") or (not answerable and status == "low_context"),
        })

    # Summary
    total = len(entries)
    answerable_qs = [e for e in entries if e["answerable"]]
    unanswerable_qs = [e for e in entries if not e["answerable"]]
    correct_cls = sum(1 for r in results if r["correct_classification"])

    print("\n" + "="*70)
    print(f"  Total questions:        {total}")
    print(f"  Classification accuracy: {correct_cls}/{total} ({correct_cls/total*100:.1f}%)")
    print(f"  Answerable -> ok:        {ok_count}/{len(answerable_qs)}")
    print(f"  Unanswerable -> refused:  {low_context_count}/{len(unanswerable_qs)+len(answerable_qs)-ok_count}")
    print(f"  Correct doc in top-1:    {correct_doc_count}/{len(answerable_qs)} ({correct_doc_count/max(len(answerable_qs),1)*100:.1f}%)")
    print(f"  Avg top score:           {total_top_score/total:.4f}")
    print(f"  Avg latency:             {total_latency/total:.1f}ms")
    print("="*70)


if __name__ == "__main__":
    run_eval()
