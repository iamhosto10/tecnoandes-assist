"""POST /ask: retrieval + generación + confianza, en ese orden. Cada paso
se guarda en `queries`/`retrieved_chunks` para poder auditar cualquier
decisión después — incluidos los casos donde la generación falló.
"""

import anthropic
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import AskRequest, AskResponse, ConfidenceBreakdown, SourceChunk
from app.confidence.rules import decide_routing
from app.confidence.scoring import compute_confidence_score
from app.confidence.signals import ConfidenceSignals
from app.db.models.queries import Query, QueryChunk
from app.db.session import get_db
from app.rag.embeddings import EmbeddingProvider, get_embedding_provider
from app.rag.generation import generate_answer, get_anthropic_client
from app.rag.retrieval import hybrid_search

router = APIRouter()

# Se usa en vez de la respuesta del modelo cuando la decisión es "review":
# ahí el modelo no dijo nada confiable (falló, citó mal, o el contexto no
# tenía la información), así que no tiene sentido mostrar lo que escribió.
REVIEW_FALLBACK_ANSWER = (
    "No tengo información suficiente para responder con seguridad en este momento. "
    "Un asesor revisará tu consulta y te contactará pronto."
)


@router.post("/ask", response_model=AskResponse)
def ask(
    body: AskRequest,
    db: Session = Depends(get_db),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    anthropic_client: anthropic.Anthropic = Depends(get_anthropic_client),
) -> AskResponse:
    chunks = hybrid_search(db, body.question, embedding_provider)
    generation = generate_answer(body.question, chunks, anthropic_client)

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
    confidence_score = compute_confidence_score(signals)
    routing = decide_routing(signals, confidence_score)

    customer_answer = (
        REVIEW_FALLBACK_ANSWER
        if routing.decision == "review"
        else (generation.answer or REVIEW_FALLBACK_ANSWER)
    )

    query = Query(
        question=body.question,
        answer=customer_answer,
        raw_model_answer=generation.answer,
        support=generation.support,
        needs_human=generation.needs_human,
        needs_human_reason=generation.needs_human_reason,
        cited_chunk_ids=generation.cited_chunk_ids,
        citation_valid=generation.citation_valid,
        retrieval_score=retrieval_score,
        retrieval_margin=retrieval_margin,
        confidence_score=confidence_score,
        decision=routing.decision,
        rule_applied=routing.rule,
        generation_error=generation.error,
        latency_ms=generation.latency_ms,
        input_tokens=generation.input_tokens,
        output_tokens=generation.output_tokens,
        cost_usd=generation.cost_usd,
    )
    db.add(query)
    db.flush()  # asegura query.id para las FKs de retrieved_chunks

    for rank, chunk in enumerate(chunks, start=1):
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
    db.commit()

    return AskResponse(
        query_id=query.id,
        answer=customer_answer,
        decision=routing.decision,
        rule_applied=routing.rule,
        confidence=ConfidenceBreakdown(
            retrieval_score=retrieval_score,
            retrieval_margin=retrieval_margin,
            support=generation.support,
            needs_human=generation.needs_human,
            citation_valid=generation.citation_valid,
            confidence_score=confidence_score,
        ),
        cited_chunk_ids=generation.cited_chunk_ids,
        sources=[
            SourceChunk(
                chunk_id=c.chunk_id,
                document_slug=c.document_slug,
                document_title=c.document_title,
                heading_path=c.heading_path,
                content=c.content,
                vector_score=c.vector_score,
                fulltext_score=c.fulltext_score,
                rrf_score=c.rrf_score,
                cited=c.chunk_id in generation.cited_chunk_ids,
            )
            for c in chunks
        ],
        latency_ms=generation.latency_ms,
        input_tokens=generation.input_tokens,
        output_tokens=generation.output_tokens,
        cost_usd=generation.cost_usd,
    )
