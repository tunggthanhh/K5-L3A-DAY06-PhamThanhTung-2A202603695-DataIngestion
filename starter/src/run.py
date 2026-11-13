"""Run the three Day 06 ingestion strategies end to end."""
import atexit, json, os, re, time
from pathlib import Path
from dotenv import load_dotenv
from .ingestion import load_pdf
from .chunking import fixed_size, by_paragraph
from .embeddings import MyEmbedder
from .store import QdrantLocalStore
from .evaluation import evaluate_query, summarize


def main() -> None:
    root = Path(__file__).resolve().parents[1]; load_dotenv(root / ".env")
    pages = load_pdf(root / "data/bo_luat_lao_dong.pdf", "bo-luat-lao-dong-2019", "data/bo_luat_lao_dong.pdf")
    if sum(bool(p.text) for p in pages) < 30: raise RuntimeError("Corpus has fewer than 30 content pages")
    chapter = None
    for page in pages:
        match = re.search(r"CHƯƠNG\s+([IVXLCDM]+)", page.text, re.I)
        if match: chapter = f"Chương {match.group(1).upper()}"
        page.metadata.update({"document_type": "Bộ luật", "year": 2019, "chapter": chapter})
    embedder = MyEmbedder(os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"))
    store = QdrantLocalStore(root / os.getenv("QDRANT_PATH", "results/qdrant"), embedder.dimensions)
    atexit.register(store.close)
    strategies = {"A": [c for p in pages for c in fixed_size(p, 500, 50)], "B": [c for p in pages for c in by_paragraph(p, 500)]}
    strategies["C"] = strategies["B"]
    for name, chunks in strategies.items(): store.upsert(name, chunks, embedder.embed_documents([c.text for c in chunks]))
    questions = json.loads((root / "data/questions.json").read_text(encoding="utf-8")); traces = []
    for question in questions:
        vector = embedder.embed_query(question["question"])
        for strategy in strategies:
            filters = question.get("filter") if strategy == "C" else None
            if filters and "chapter" in filters: filters = {**filters, "chapter": filters["chapter"].split(" - ")[0]}
            trace = evaluate_query(question, store.search(strategy, vector, filters=filters)); trace["strategy"] = strategy; traces.append(trace)
    out = root / "results"; out.mkdir(exist_ok=True)
    (out / "traces.json").write_text(json.dumps(traces, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "metrics.json").write_text(json.dumps(summarize(traces), ensure_ascii=False, indent=2), encoding="utf-8")
    store.close()
    print(f"Completed {len(traces)} query traces in {time.strftime('%H:%M:%S')}")


if __name__ == "__main__":
    main()
