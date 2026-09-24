"""Endpoints de la consola de revisión: cola, detalle, acciones y
re-prueba. Protegidos con el token de `REVIEW_CONSOLE_TOKEN` — a
diferencia de /ask, que es público (lo usa el chat del cliente).
"""

import datetime as dt

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query as QueryParam
from sqlalchemy.orm import Session

from app.api.review_schemas import (
    RetestResponse,
    RetestSnapshot,
    ReviewActionOut,
    ReviewActionRequest,
    ReviewItemDetail,
    ReviewItemListResponse,
    ReviewItemSummary,
)
from app.api.schemas import ConfidenceBreakdown, SourceChunk
from app.core.security import require_review_console_token
from app.db.models.review import ReviewItem
from app.db.session import get_db
from app.rag.embeddings import EmbeddingProvider, get_embedding_provider
from app.rag.generation import get_anthropic_client
from app.rag.pipeline import run_ask_pipeline
from app.review.actions import NewDocumentInput, ReviewActionError, apply_review_action
from app.review.queue import list_review_items

router = APIRouter(prefix="/review", dependencies=[Depends(require_review_console_token)])


def _get_review_item_or_404(db: Session, item_id: int) -> ReviewItem:
    item = db.get(ReviewItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Caso de revisión no encontrado")
    return item


def _to_detail(item: ReviewItem) -> ReviewItemDetail:
    query = item.query
    return ReviewItemDetail(
        id=item.id,
        status=item.status,
        reason=item.reason,
        created_at=item.created_at,
        resolved_at=item.resolved_at,
        resolved_by=item.resolved_by,
        question=query.question,
        answer=query.answer,
        raw_model_answer=query.raw_model_answer,
        decision=query.decision,
        rule_applied=query.rule_applied,
        confidence=ConfidenceBreakdown(
            retrieval_score=query.retrieval_score,
            retrieval_margin=query.retrieval_margin,
            support=query.support,
            needs_human=query.needs_human,
            citation_valid=query.citation_valid,
            confidence_score=query.confidence_score,
        ),
        sources=[
            SourceChunk(
                chunk_id=qc.chunk_id,
                document_slug=qc.chunk.document.slug,
                document_title=qc.chunk.document.title,
                heading_path=qc.chunk.heading_path,
                content=qc.chunk.content,
                vector_score=qc.vector_score,
                fulltext_score=qc.fulltext_score,
                rrf_score=qc.rrf_score,
                cited=qc.chunk_id in query.cited_chunk_ids,
            )
            for qc in query.retrieved_chunks
        ],
        actions=[
            ReviewActionOut(
                id=a.id,
                action_type=a.action_type,
                note=a.note,
                actor=a.actor,
                document_id=a.document_id,
                created_at=a.created_at,
            )
            for a in item.actions
        ],
    )


@router.get("/items", response_model=ReviewItemListResponse)
def get_review_items(
    status: str | None = None,
    reason: str | None = None,
    confidence_min: float | None = None,
    confidence_max: float | None = None,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    limit: int = QueryParam(default=20, ge=1, le=100),
    offset: int = QueryParam(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ReviewItemListResponse:
    result = list_review_items(
        db,
        status=status,
        reason=reason,
        confidence_min=confidence_min,
        confidence_max=confidence_max,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return ReviewItemListResponse(
        items=[
            ReviewItemSummary(
                id=item.id,
                status=item.status,
                reason=item.reason,
                created_at=item.created_at,
                resolved_at=item.resolved_at,
                question=item.query.question,
                decision=item.query.decision,
                confidence_score=item.query.confidence_score,
            )
            for item in result.items
        ],
        total=result.total,
        limit=limit,
        offset=offset,
    )


@router.get("/items/{item_id}", response_model=ReviewItemDetail)
def get_review_item(item_id: int, db: Session = Depends(get_db)) -> ReviewItemDetail:
    item = _get_review_item_or_404(db, item_id)
    return _to_detail(item)


@router.post("/items/{item_id}/actions", response_model=ReviewItemDetail)
def post_review_action(
    item_id: int,
    body: ReviewActionRequest,
    db: Session = Depends(get_db),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
) -> ReviewItemDetail:
    item = _get_review_item_or_404(db, item_id)

    new_document = (
        NewDocumentInput(
            slug=body.new_document.slug,
            title=body.new_document.title,
            category=body.new_document.category,
            content=body.new_document.content,
        )
        if body.new_document is not None
        else None
    )

    try:
        apply_review_action(
            db,
            item,
            embedding_provider,
            action_type=body.action_type,
            actor=body.actor,
            note=body.note,
            corrected_answer=body.corrected_answer,
            new_document=new_document,
            document_id=body.document_id,
            document_content=body.document_content,
        )
    except ReviewActionError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.commit()
    db.refresh(item)
    return _to_detail(item)


@router.post("/items/{item_id}/retest", response_model=RetestResponse)
def retest_review_item(
    item_id: int,
    db: Session = Depends(get_db),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    anthropic_client: anthropic.Anthropic = Depends(get_anthropic_client),
) -> RetestResponse:
    item = _get_review_item_or_404(db, item_id)
    original = item.query

    result = run_ask_pipeline(original.question, db, embedding_provider, anthropic_client)

    return RetestResponse(
        before=RetestSnapshot(
            answer=original.answer,
            decision=original.decision,
            confidence_score=original.confidence_score,
            support=original.support,
        ),
        after=RetestSnapshot(
            answer=result.customer_answer,
            decision=result.routing.decision,
            confidence_score=result.confidence_score,
            support=result.generation.support,
        ),
    )
