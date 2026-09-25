"""Brechas de conocimiento: agrupa por similitud de embeddings las
preguntas que terminaron en support=none — sin tabla persistida (Fase 0,
decisión #5 en CLAUDE.md), se recalcula en cada request. A esta escala
(cientos de casos) es instantáneo; si algún día no lo fuera, cachear
sería el siguiente paso, no construirlo de una vez.

`_cluster_questions` está separado del resto para que la lógica de
agrupamiento se pueda testear sola, sin base de datos — mismo patrón que
`reciprocal_rank_fusion` en app/rag/retrieval.py.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.queries import Query
from app.rag.embeddings import EmbeddingProvider


@dataclass
class KnowledgeGapGroup:
    representative_question: str
    count: int
    example_questions: list[str]
    query_ids: list[int]


def _cluster_questions(
    questions: list[str],
    embedding_provider: EmbeddingProvider,
    distance_threshold: float,
) -> list[list[int]]:
    """Devuelve grupos de ÍNDICES de `questions` (no ids de DB) que caen
    en el mismo cluster. AgglomerativeClustering con distancia coseno:
    no hay que decidir de antemano cuántos grupos van a salir, a
    diferencia de k-means — apropiado acá porque el número de "temas"
    entre las preguntas sin soporte es desconocido.
    """
    if len(questions) < 2:
        return [[i] for i in range(len(questions))]

    embeddings = np.array([embedding_provider.embed_query(q) for q in questions])

    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold,
        metric="cosine",
        linkage="average",
    )
    labels = clustering.fit_predict(embeddings)

    groups: dict[int, list[int]] = {}
    for index, label in enumerate(labels):
        groups.setdefault(int(label), []).append(index)
    return list(groups.values())


def find_knowledge_gaps(
    session: Session,
    embedding_provider: EmbeddingProvider,
    min_group_size: int = 2,
) -> list[KnowledgeGapGroup]:
    rows = list(
        session.scalars(
            select(Query).where(Query.support == "none").order_by(Query.created_at.desc())
        )
    )
    if len(rows) < min_group_size:
        return []

    settings = get_settings()
    questions = [r.question for r in rows]
    index_groups = _cluster_questions(
        questions, embedding_provider, settings.knowledge_gap_distance_threshold
    )

    result = []
    for indices in index_groups:
        if len(indices) < min_group_size:
            continue
        members = [rows[i] for i in indices]
        # La más corta suele ser la formulación más "genérica" del grupo
        # (menos detalles específicos de una sola persona).
        representative = min(members, key=lambda r: len(r.question))
        result.append(
            KnowledgeGapGroup(
                representative_question=representative.question,
                count=len(members),
                example_questions=[m.question for m in members[:5]],
                query_ids=[m.id for m in members],
            )
        )

    result.sort(key=lambda g: g.count, reverse=True)
    return result
