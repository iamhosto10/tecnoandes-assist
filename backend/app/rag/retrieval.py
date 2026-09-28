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

from collections import Counter
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.rag.embeddings import EmbeddingProvider

# Constante estándar en la literatura de RRF; el resultado final es poco sensible a este valor.
RRF_K = 60

# "Parent-document retrieval": si un mismo documento DOMINA el top de
# candidatos, es señal de que la pregunta es amplia (p.ej. "¿qué
# celulares tienen?") y `top_k` fragmentos sueltos no van a alcanzar para
# cubrir todo el catálogo de esa categoría.
#
# Un simple conteo ("aparece 3+ veces") no alcanza: los productos de una
# misma categoría se parecen mucho entre sí en texto, así que incluso una
# pregunta puntual ("¿cuánto cuesta el iPhone 13?") trae 3-4 celulares
# más entre los primeros 10 candidatos, sin que eso signifique que haya
# que traer el catálogo completo — el chunk correcto sigue siendo,
# claramente, el más relevante de todos. Medido empíricamente contra
# preguntas puntuales y amplias reales: lo que sí separa los dos casos es
# que el documento dominante se lleve una MAYORÍA holgada del top (>70%),
# no solo una pluralidad. Es un heurístico, no una regla exacta — prioriza
# no encarecer preguntas puntuales por encima de detectar cada pregunta
# amplia posible.
DOCUMENT_MERGE_SCAN_SIZE = 10
DOCUMENT_MERGE_MIN_SHARE = 0.7


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

_DOCUMENT_ID_BY_CHUNK_SQL = text("""
    SELECT id AS chunk_id, document_id FROM chunks WHERE id = ANY(:chunk_ids)
""")

_CHUNK_IDS_BY_DOCUMENT_SQL = text("""
    SELECT id FROM chunks WHERE document_id = :document_id ORDER BY chunk_index
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

    ranked_ids = sorted(fused_scores, key=fused_scores.get, reverse=True)
    final_ids = _select_ids_with_document_merge(session, ranked_ids, resolved_top_k)

    vector_score_by_id = {row["chunk_id"]: float(row["score"]) for row in vector_rows}
    fulltext_score_by_id = {row["chunk_id"]: float(row["score"]) for row in fulltext_rows}
    vector_rank_by_id = {chunk_id: rank for rank, chunk_id in enumerate(vector_ranked_ids, start=1)}
    fulltext_rank_by_id = {
        chunk_id: rank for rank, chunk_id in enumerate(fulltext_ranked_ids, start=1)
    }

    chunk_rows = session.execute(_CHUNKS_BY_ID_SQL, {"chunk_ids": final_ids}).mappings().all()
    chunk_by_id = {row["chunk_id"]: row for row in chunk_rows}

    return [
        RetrievedChunk(
            chunk_id=chunk_id,
            document_id=chunk_by_id[chunk_id]["document_id"],
            document_title=chunk_by_id[chunk_id]["document_title"],
            document_slug=chunk_by_id[chunk_id]["document_slug"],
            heading_path=chunk_by_id[chunk_id]["heading_path"],
            content=chunk_by_id[chunk_id]["content"],
            # Los chunks que entraron por el merge de documento completo (ver
            # _select_ids_with_document_merge) no fueron rankeados de forma
            # independiente por ninguna de las dos búsquedas — 0.0/None es
            # honesto acá, no un valor inventado.
            vector_score=vector_score_by_id.get(chunk_id, 0.0),
            fulltext_score=fulltext_score_by_id.get(chunk_id, 0.0),
            rrf_score=fused_scores.get(chunk_id, 0.0),
            vector_rank=vector_rank_by_id.get(chunk_id),
            fulltext_rank=fulltext_rank_by_id.get(chunk_id),
        )
        for chunk_id in final_ids
    ]


def _select_ids_with_document_merge(
    session: Session, ranked_ids: list[int], top_k: int
) -> list[int]:
    """Decide qué chunks devolver: hasta `top_k` candidatos individuales,
    salvo que varios de los mejor rankeados (ver DOCUMENT_MERGE_*) apunten
    al mismo documento — en ese caso ese documento se trae COMPLETO (todos
    sus chunks, en orden), en vez de solo los fragmentos sueltos que
    aparecieron en el ranking. Los documentos mergeados no consumen el
    presupuesto de `top_k`: son un extra deliberado para preguntas amplias,
    no un reemplazo de las preguntas puntuales.
    """
    scan_ids = ranked_ids[:DOCUMENT_MERGE_SCAN_SIZE]
    doc_id_rows = (
        session.execute(_DOCUMENT_ID_BY_CHUNK_SQL, {"chunk_ids": ranked_ids}).mappings().all()
    )
    doc_id_by_chunk = {row["chunk_id"]: row["document_id"] for row in doc_id_rows}

    doc_counts = Counter(doc_id_by_chunk[cid] for cid in scan_ids if cid in doc_id_by_chunk)
    merge_doc_ids = {
        doc_id
        for doc_id, count in doc_counts.items()
        if scan_ids and count / len(scan_ids) > DOCUMENT_MERGE_MIN_SHARE
    }

    final_ids: list[int] = []
    added_docs: set[int] = set()
    individual_count = 0

    for chunk_id in ranked_ids:
        doc_id = doc_id_by_chunk.get(chunk_id)
        if doc_id in merge_doc_ids:
            if doc_id not in added_docs:
                added_docs.add(doc_id)
                doc_chunk_rows = (
                    session.execute(_CHUNK_IDS_BY_DOCUMENT_SQL, {"document_id": doc_id})
                    .mappings()
                    .all()
                )
                final_ids.extend(row["id"] for row in doc_chunk_rows)
            continue
        if individual_count < top_k:
            final_ids.append(chunk_id)
            individual_count += 1

    return final_ids
