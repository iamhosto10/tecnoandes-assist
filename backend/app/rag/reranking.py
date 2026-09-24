"""Reranking opcional (cross-encoder) sobre los candidatos que ya pasaron RRF.

Un cross-encoder ve la pregunta y el chunk JUNTOS en una sola pasada por
el modelo (a diferencia de los embeddings, que los codifican por separado
y luego se comparan) y por eso puntúa la relevancia con más precisión —
a costa de ser mucho más lento. Por eso solo tiene sentido aplicarlo
sobre los pocos candidatos que ya devolvió el retrieval híbrido, nunca
sobre todo el corpus. Desactivado por defecto (RERANKER_ENABLED=false);
`hybrid_search` ya deja un orden razonable sin él.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import get_settings
from app.rag.retrieval import RetrievedChunk

DEFAULT_CROSS_ENCODER_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"


class Reranker(ABC):
    @abstractmethod
    def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]: ...


class NoopReranker(Reranker):
    def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        return chunks


class CrossEncoderReranker(Reranker):
    def __init__(self, model_name: str = DEFAULT_CROSS_ENCODER_MODEL) -> None:
        from sentence_transformers import CrossEncoder

        self._model = CrossEncoder(model_name)

    def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if not chunks:
            return chunks
        pairs = [(query, chunk.content) for chunk in chunks]
        scores = self._model.predict(pairs)
        order = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)
        return [chunks[i] for i in order]


@lru_cache
def get_reranker() -> Reranker:
    if get_settings().reranker_enabled:
        return CrossEncoderReranker()
    return NoopReranker()
