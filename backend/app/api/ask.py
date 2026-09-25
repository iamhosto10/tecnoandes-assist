"""POST /ask: retrieval + generación + confianza, en ese orden (el
pipeline en sí vive en app/rag/pipeline.py, compartido con
/review/items/{id}/retest). Cada paso se guarda en
`queries`/`retrieved_chunks` para poder auditar cualquier decisión
después — incluidos los casos donde la generación falló. Toda decisión
distinta de "direct" crea además un caso en la cola de revisión.
"""

import anthropic
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import AskRequest, AskResponse, ConfidenceBreakdown, SourceChunk
from app.db.models.queries import Query, QueryChunk
from app.db.models.review import ReviewItem
from app.db.session import get_db
from app.rag.embeddings import EmbeddingProvider, get_embedding_provider
from app.rag.generation import get_anthropic_client
from app.rag.pipeline import run_ask_pipeline

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask(
    body: AskRequest,
    db: Session = Depends(get_db),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    anthropic_client: anthropic.Anthropic = Depends(get_anthropic_client),
) -> AskResponse:
    result = run_ask_pipeline(body.question, db, embedding_provider, anthropic_client)
    generation = result.generation

    query = Query(
        question=body.question,
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

    db.commit()

    return AskResponse(
        query_id=query.id,
        answer=result.customer_answer,
        decision=result.routing.decision,
        rule_applied=result.routing.rule,
        confidence=ConfidenceBreakdown.from_domain(result.signals, result.score_breakdown),
        cited_chunk_ids=generation.cited_chunk_ids,
        sources=[
            SourceChunk(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                document_slug=c.document_slug,
                document_title=c.document_title,
                heading_path=c.heading_path,
                content=c.content,
                vector_score=c.vector_score,
                fulltext_score=c.fulltext_score,
                rrf_score=c.rrf_score,
                cited=c.chunk_id in generation.cited_chunk_ids,
            )
            for c in result.chunks
        ],
        latency_ms=generation.latency_ms,
        input_tokens=generation.input_tokens,
        output_tokens=generation.output_tokens,
        cost_usd=generation.cost_usd,
    )
