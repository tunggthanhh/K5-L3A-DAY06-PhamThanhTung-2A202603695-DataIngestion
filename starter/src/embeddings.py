"""Local, real embeddings for Vietnamese retrieval using Sentence Transformers."""
from typing import Protocol


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    """Embed text locally with a Sentence Transformers model.

    The default model is multilingual and therefore suitable for the Vietnamese
    legal corpus. It is downloaded once on the first run and then cached by
    Hugging Face. Vectors are L2-normalized, so pgvector cosine search is
    consistent for both document and query embeddings.
    """

    def __init__(self, model_name: str) -> None:
        if not model_name or not model_name.strip():
            raise ValueError("model_name is required; set EMBEDDING_MODEL in .env")

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed. Run: "
                "python -m pip install -r requirements.txt"
            ) from exc

        self.model_name = model_name.strip()
        try:
            self._model = SentenceTransformer(self.model_name)
        except Exception as exc:
            raise RuntimeError(
                f"Could not load embedding model {self.model_name!r}. "
                "Check your internet connection for the first download, or use "
                "a locally cached model name."
            ) from exc

        self.dimensions = int(self._model.get_sentence_embedding_dimension())
        if self.dimensions <= 0:
            raise RuntimeError(f"Model {self.model_name!r} reported invalid dimensions")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one normalized vector per non-empty document chunk."""
        self._validate_texts(texts, "documents")
        if not texts:
            return []
        vectors = self._model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return [[float(value) for value in vector] for vector in vectors]

    def embed_query(self, question: str) -> list[float]:
        """Return one normalized vector compatible with document vectors."""
        self._validate_texts([question], "query")
        vector = self._model.encode(
            question,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return [float(value) for value in vector]

    @staticmethod
    def _validate_texts(texts: list[str], label: str) -> None:
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError(f"{label} must contain only non-empty strings")
