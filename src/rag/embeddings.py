from __future__ import annotations

from functools import lru_cache
from typing import Iterable

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class LocalEmbedder:
    """CPU embeddings through FastEmbed; source text stays on this machine."""

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        from fastembed import TextEmbedding

        self.model_name = model_name
        self._model = TextEmbedding(model_name=model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._model.embed(texts, batch_size=32)]

    def embed_query(self, text: str) -> list[float]:
        vector = next(self._model.embed([text]))
        return vector.tolist()


@lru_cache(maxsize=1)
def get_local_embedder(model_name: str = DEFAULT_EMBEDDING_MODEL) -> LocalEmbedder:
    """Load one local embedding model and reuse it within the process."""
    return LocalEmbedder(model_name=model_name)
