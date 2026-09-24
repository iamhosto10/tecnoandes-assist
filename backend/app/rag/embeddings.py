"""Interfaz de embeddings.

Detrás de `EmbeddingProvider` puede haber un modelo local (E5 vía
sentence-transformers, el que se usa por defecto: sin costo ni API key)
o más adelante un proveedor por API (p.ej. Voyage AI) sin que el resto
del pipeline RAG — chunking, ingesta, retrieval — tenga que cambiar.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import get_settings


class EmbeddingProvider(ABC):
    dimensions: int

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embedding de una pregunta del usuario."""

    @abstractmethod
    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        """Embeddings de fragmentos de la base de conocimiento (batch)."""

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Usado por el chunking para medir el tamaño real en tokens del modelo."""


class E5EmbeddingProvider(EmbeddingProvider):
    """intfloat/multilingual-e5-small (384 dim).

    E5 se entrenó distinguiendo el rol del texto con los prefijos
    "query: " / "passage: " — sin ellos la calidad del retrieval baja
    notablemente, porque el modelo no sabe si está viendo una pregunta o
    un fragmento de la base de conocimiento.
    """

    def __init__(self, model_name: str | None = None) -> None:
        from sentence_transformers import SentenceTransformer

        settings = get_settings()
        self._model = SentenceTransformer(model_name or settings.embedding_model)
        self.dimensions = settings.embedding_dimensions

    def embed_query(self, text: str) -> list[float]:
        vector = self._model.encode(f"query: {text}", normalize_embeddings=True)
        return vector.tolist()

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        prefixed = [f"passage: {t}" for t in texts]
        vectors = self._model.encode(prefixed, normalize_embeddings=True)
        return vectors.tolist()

    def count_tokens(self, text: str) -> int:
        return len(self._model.tokenizer.encode(text, add_special_tokens=False))


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    # Cachea el modelo (pesado de cargar, ~470MB) durante todo el proceso.
    return E5EmbeddingProvider()
