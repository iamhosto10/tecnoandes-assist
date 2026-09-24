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
