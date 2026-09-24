"""Retrieval híbrido: búsqueda vectorial + texto completo, fusionadas con RRF.

Se corren dos consultas SQL independientes y simples (una por similitud
vectorial, otra por texto completo) y la fusión se hace en Python con
`reciprocal_rank_fusion`, en vez de un único CTE gigante: así cada
consulta se puede depurar por separado (EXPLAIN, probarla a mano) y la
fórmula de RRF queda como una función pura, fácil de leer y de testear
sin necesitar una base de datos levantada.

RRF combina la POSICIÓN de cada chunk en cada ranking, no sus puntajes
crudos: `score = sum(1 / (k + rank))` sobre cada método donde aparece. Se
usa en vez de sumar los puntajes directamente porque la similitud coseno
(0-1) y el `ts_rank` de Postgres (una escala arbitraria que depende de la
frecuencia de términos en el corpus) no son comparables entre sí —
sumarlos le daría más peso al método que "por casualidad" produce
números más grandes. Al depender solo del rango, RRF es inmune a esa
diferencia de escalas.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.rag.embeddings import EmbeddingProvider

# Constante estándar en la literatura de RRF; el resultado final es poco sensible a este valor.
RRF_K = 60


@dataclass
class RetrievedChunk:
    chunk_id: int
    document_id: int
    document_title: str
    document_slug: str
    heading_path: str
    content: str
    vector_score: float
    fulltext_score: float
    rrf_score: float
    vector_rank: int | None
    fulltext_rank: int | None


def reciprocal_rank_fusion(ranked_lists: list[list[int]], k: int = RRF_K) -> dict[int, float]:
    """Fusiona varios rankings (listas de ids, el mejor primero) en un solo
    puntaje por id: `sum(1 / (k + rank))` sobre las listas en las que
    aparece, con `rank` empezando en 1. Un id que no aparece en una lista
    simplemente no suma nada por esa lista — no hace falta que las listas
    tengan el mismo tamaño ni los mismos elementos.
    """
    scores: dict[int, float] = {}
    for ranked_ids in ranked_lists:
        for rank, item_id in enumerate(ranked_ids, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return scores


_VECTOR_SEARCH_SQL = text("""
    SELECT c.id AS chunk_id, 1 - (c.embedding <=> CAST(:query_embedding AS vector)) AS score
    FROM chunks c
    JOIN documents d ON d.id = c.document_id
    WHERE d.is_active
    ORDER BY c.embedding <=> CAST(:query_embedding AS vector)
    LIMIT :candidate_pool
""")

_FULLTEXT_SEARCH_SQL = text("""
    SELECT c.id AS chunk_id, ts_rank(c.content_tsv, query) AS score
    FROM chunks c
    JOIN documents d ON d.id = c.document_id
    CROSS JOIN plainto_tsquery('spanish_unaccent', :query_text) AS query
    WHERE d.is_active AND c.content_tsv @@ query
    ORDER BY ts_rank(c.content_tsv, query) DESC
    LIMIT :candidate_pool
""")

_CHUNKS_BY_ID_SQL = text("""
    SELECT c.id AS chunk_id, c.document_id, d.title AS document_title, d.slug AS document_slug,
           c.heading_path, c.content
    FROM chunks c
    JOIN documents d ON d.id = c.document_id
    WHERE c.id = ANY(:chunk_ids)
""")


def _format_vector_literal(vector: list[float]) -> str:
    # Formato de texto que pgvector entiende para castear a `vector`: sin
    # espacios, para no depender de qué tan permisivo sea el parser.
    return "[" + ",".join(repr(float(x)) for x in vector) + "]"


def hybrid_search(
    session: Session,
    query: str,
    embedding_provider: EmbeddingProvider,
    top_k: int | None = None,
    candidate_pool: int = 20,
) -> list[RetrievedChunk]:
    settings = get_settings()
    resolved_top_k = top_k if top_k is not None else settings.retrieval_top_k
    query_embedding = embedding_provider.embed_query(query)

    vector_rows = (
        session.execute(
            _VECTOR_SEARCH_SQL,
            {
                "query_embedding": _format_vector_literal(query_embedding),
                "candidate_pool": candidate_pool,
            },
        )
        .mappings()
        .all()
    )
    fulltext_rows = (
        session.execute(
            _FULLTEXT_SEARCH_SQL, {"query_text": query, "candidate_pool": candidate_pool}
        )
        .mappings()
        .all()
    )

    vector_ranked_ids = [row["chunk_id"] for row in vector_rows]
    fulltext_ranked_ids = [row["chunk_id"] for row in fulltext_rows]
    fused_scores = reciprocal_rank_fusion([vector_ranked_ids, fulltext_ranked_ids])

    if not fused_scores:
        return []

    top_ids = sorted(fused_scores, key=fused_scores.get, reverse=True)[:resolved_top_k]

    vector_score_by_id = {row["chunk_id"]: float(row["score"]) for row in vector_rows}
    fulltext_score_by_id = {row["chunk_id"]: float(row["score"]) for row in fulltext_rows}
    vector_rank_by_id = {chunk_id: rank for rank, chunk_id in enumerate(vector_ranked_ids, start=1)}
    fulltext_rank_by_id = {
        chunk_id: rank for rank, chunk_id in enumerate(fulltext_ranked_ids, start=1)
    }

    chunk_rows = session.execute(_CHUNKS_BY_ID_SQL, {"chunk_ids": top_ids}).mappings().all()
    chunk_by_id = {row["chunk_id"]: row for row in chunk_rows}

    return [
        RetrievedChunk(
            chunk_id=chunk_id,
            document_id=chunk_by_id[chunk_id]["document_id"],
            document_title=chunk_by_id[chunk_id]["document_title"],
            document_slug=chunk_by_id[chunk_id]["document_slug"],
            heading_path=chunk_by_id[chunk_id]["heading_path"],
            content=chunk_by_id[chunk_id]["content"],
            vector_score=vector_score_by_id.get(chunk_id, 0.0),
            fulltext_score=fulltext_score_by_id.get(chunk_id, 0.0),
            rrf_score=fused_scores[chunk_id],
            vector_rank=vector_rank_by_id.get(chunk_id),
            fulltext_rank=fulltext_rank_by_id.get(chunk_id),
        )
        for chunk_id in top_ids
    ]
