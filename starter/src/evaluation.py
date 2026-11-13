"""Evaluate retrieved evidence and preserve auditable per-query traces."""
from typing import Any
import re
import unicodedata


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    gold = _norm(question["evidence_quote"])
    def check(hit: dict[str, Any]) -> bool:
        meta = hit["metadata"]
        source_ok = meta.get("document_id") == question["gold_source_id"]
        page = question.get("gold_page")
        page_ok = page is None or meta.get("page") == page
        return source_ok and page_ok and gold in _norm(hit["text"])
    labelled = [{**hit, "evidence_hit": check(hit)} for hit in hits]
    return {"question_id": question["id"], "split": question["split"], "question": question["question"], "gold_page": question.get("gold_page"), "page_verified": question.get("gold_page") is not None, "hits": labelled, "hit_at_1": bool(labelled and labelled[0]["evidence_hit"]), "evidence_hit_at_3": any(hit["evidence_hit"] for hit in labelled[:3])}


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for strategy in sorted({trace["strategy"] for trace in traces}):
        result[strategy] = {}
        for split in ("dev", "test"):
            rows = [t for t in traces if t["strategy"] == strategy and t["split"] == split]
            n = len(rows)
            result[strategy][split] = {"n": n, "hit_at_1": f"{sum(t['hit_at_1'] for t in rows)}/{n}", "evidence_hit_at_3": f"{sum(t['evidence_hit_at_3'] for t in rows)}/{n}", "page_verified_questions": sum(t["page_verified"] for t in rows)}
    return result

def _norm(text: str) -> str:
    """Compare evidence robustly despite PDF extraction inserting inner spaces."""
    normalized = unicodedata.normalize("NFD", text.casefold()).replace("đ", "d")
    return "".join(char for char in normalized if char.isalnum() and unicodedata.category(char) != "Mn")
