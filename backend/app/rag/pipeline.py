"""El pipeline completo detrás de una pregunta: retrieval -> generación ->
señales de confianza -> enrutamiento. Vive separado de `app/api/ask.py`
para que `POST /review/items/{id}/retest` (Fase 3) pueda reusarlo sin
duplicar la lógica ni pasar por HTTP — retest corre exactamente el mismo
pipeline contra la base actual, solo que no persiste una Query nueva.
"""

from __future__ import annotations

from dataclasses import dataclass

import anthropic
from sqlalchemy.orm import Session

from app.confidence.rules import RoutingResult, decide_routing
from app.confidence.scoring import ConfidenceScoreBreakdown, compute_confidence_score
from app.confidence.signals import ConfidenceSignals
from app.db.models.queries import Query, QueryChunk
from app.db.models.review import ReviewItem
from app.rag.embeddings import EmbeddingProvider
from app.rag.generation import GenerationResult, generate_answer
from app.rag.retrieval import RetrievedChunk, hybrid_search

# Se usa en vez de la respuesta del modelo cuando la decisión es "review":
# ahí el modelo no dijo nada confiable (falló, citó mal, o el contexto no
# tenía la información), así que no tiene sentido mostrar lo que escribió.
REVIEW_FALLBACK_ANSWER = (
    "No tengo información suficiente para responder con seguridad en este momento. "
    "Un asesor revisará tu consulta y te contactará pronto."
)


@dataclass
class AskPipelineResult:
    chunks: list[RetrievedChunk]
    generation: GenerationResult
    signals: ConfidenceSignals
    score_breakdown: ConfidenceScoreBreakdown
    confidence_score: float
    routing: RoutingResult
    customer_answer: str


def run_ask_pipeline(
    question: str,
    db: Session,
    embedding_provider: EmbeddingProvider,
    anthropic_client: anthropic.Anthropic,
) -> AskPipelineResult:
    chunks = hybrid_search(db, question, embedding_provider)
    generation = generate_answer(question, chunks, anthropic_client)

    retrieval_score = chunks[0].vector_score if chunks else 0.0
    retrieval_margin = chunks[0].vector_score - chunks[1].vector_score if len(chunks) >= 2 else 0.0

    signals = ConfidenceSignals(
        retrieval_score=retrieval_score,
        retrieval_margin=retrieval_margin,
        support=generation.support,
        needs_human=generation.needs_human,
        citation_valid=generation.citation_valid,
        generation_error=generation.error,
    )
    score_breakdown = compute_confidence_score(signals)
    routing = decide_routing(signals, score_breakdown.total)

    customer_answer = (
        REVIEW_FALLBACK_ANSWER
        if routing.decision == "review"
        else (generation.answer or REVIEW_FALLBACK_ANSWER)
    )

    return AskPipelineResult(
        chunks=chunks,
        generation=generation,
        signals=signals,
        score_breakdown=score_breakdown,
        confidence_score=score_breakdown.total,
        routing=routing,
        customer_answer=customer_answer,
    )


def persist_ask_result(question: str, result: AskPipelineResult, db: Session) -> Query:
    """Guarda una `Query` + sus `QueryChunk` y, si aplica, crea el
    `ReviewItem` correspondiente. Factorizado desde `app/api/ask.py` para
    que `scripts/seed_demo.py` (Fase 7) pueda generar casos de demo
    reales sin duplicar esta persistencia — ambos corren exactamente el
    mismo camino que produce un caso en la cola de revisión.
    """
    generation = result.generation
    query = Query(
        question=question,
        answer=result.customer_answer,
        raw_model_answer=generation.answer,
        support=generation.support,
        needs_human=generation.needs_human,
        needs_human_reason=generation.needs_human_reason,
        cited_chunk_ids=generation.cited_chunk_ids,
        citation_valid=generation.citation_valid,
        retrieval_score=result.signals.retrieval_score,
        retrieval_margin=result.signals.retrieval_margin,
        confidence_score=result.confidence_score,
        decision=result.routing.decision,
        rule_applied=result.routing.rule,
        generation_error=generation.error,
        latency_ms=generation.latency_ms,
        input_tokens=generation.input_tokens,
        output_tokens=generation.output_tokens,
        cost_usd=generation.cost_usd,
    )
    db.add(query)
    db.flush()  # asegura query.id para las FKs de retrieved_chunks / review_items

    for rank, chunk in enumerate(result.chunks, start=1):
        db.add(
            QueryChunk(
                query_id=query.id,
                chunk_id=chunk.chunk_id,
                rank=rank,
                vector_score=chunk.vector_score,
                fulltext_score=chunk.fulltext_score,
                rrf_score=chunk.rrf_score,
            )
        )

    if result.routing.decision != "direct":
        db.add(ReviewItem(query_id=query.id, status="pending", reason=result.routing.rule))

    return query
