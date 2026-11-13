"""Persistent local Qdrant vector store; Docker is not required."""
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5
from qdrant_client import QdrantClient, models
from .models import Chunk

class QdrantLocalStore:
    collection_name = "day6_chunks"
    allowed_filters = {"document_id", "source", "page", "document_type", "year", "chapter", "chunking"}

    def __init__(self, storage_path: str | Path, dimensions: int) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be greater than zero")
        self.dimensions = dimensions
        self.client = QdrantClient(path=str(Path(storage_path)))

    def create_schema(self) -> None:
        if self.client.collection_exists(self.collection_name):
            size = self.client.get_collection(self.collection_name).config.params.vectors.size
            if size != self.dimensions:
                raise ValueError(f"Existing collection uses {size} dimensions, expected {self.dimensions}")
            return
        self.client.create_collection(self.collection_name, vectors_config=models.VectorParams(size=self.dimensions, distance=models.Distance.COSINE))

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        self._validate(vectors); self.create_schema()
        selector = models.FilterSelector(filter=models.Filter(must=[models.FieldCondition(key="strategy", match=models.MatchValue(value=strategy))]))
        self.client.delete(self.collection_name, points_selector=selector, wait=True)
        points = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            meta = dict(chunk.metadata)
            payload = {"strategy": strategy, "chunk_id": chunk.chunk_id, "document_id": chunk.document_id, "source": chunk.source, "page": chunk.page, "text": chunk.text, "metadata": meta}
            payload.update({key: meta[key] for key in self.allowed_filters if key in meta})
            points.append(models.PointStruct(id=str(uuid5(NAMESPACE_URL, strategy + ":" + chunk.chunk_id)), vector=vector, payload=payload))
        if points:
            self.client.upsert(self.collection_name, points=points, wait=True)

    def search(self, strategy: str, query_vector: list[float], top_k: int = 3,
               filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")
        self._validate([query_vector]); self.create_schema()
        conditions = [models.FieldCondition(key="strategy", match=models.MatchValue(value=strategy))]
        for key, value in (filters or {}).items():
            if key not in self.allowed_filters or not isinstance(value, (str, int, bool)):
                raise ValueError(f"Unsupported filter: {key}")
            conditions.append(models.FieldCondition(key=key, match=models.MatchValue(value=value)))
        response = self.client.query_points(self.collection_name, query=query_vector, query_filter=models.Filter(must=conditions), limit=top_k, with_payload=True)
        return [{"chunk_id": point.payload["chunk_id"], "text": point.payload["text"], "score": float(point.score), "metadata": {"document_id": point.payload["document_id"], "source": point.payload["source"], "page": point.payload["page"], **point.payload.get("metadata", {})}} for point in response.points]

    def close(self) -> None:
        self.client.close()

    def _validate(self, vectors: list[list[float]]) -> None:
        for vector in vectors:
            if len(vector) != self.dimensions:
                raise ValueError(f"Expected {self.dimensions}-dimension vectors")
