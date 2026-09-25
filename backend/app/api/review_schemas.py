"""Esquemas Pydantic de los endpoints de revisión y de documentos."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.api.schemas import ConfidenceBreakdown, RuleApplied, SourceChunk
from app.confidence.rules import Decision

ActionType = Literal[
    "approve",
    "correct",
    "correct_and_create_document",
    "correct_and_edit_document",
    "escalate",
    "discard",
]

# Espejo de _STATUS_BY_ACTION en app/review/actions.py, más el estado inicial.
ReviewStatus = Literal["pending", "approved", "corrected", "escalated", "discarded"]


class ReviewItemSummary(BaseModel):
    id: int
    status: ReviewStatus
    reason: RuleApplied
    created_at: datetime
    resolved_at: datetime | None
    question: str
    decision: Decision
    confidence_score: float


class ReviewItemListResponse(BaseModel):
    items: list[ReviewItemSummary]
    total: int
    limit: int
    offset: int


class ReviewActionOut(BaseModel):
    id: int
    action_type: ActionType
    note: str | None
    actor: str
    document_id: int | None
    created_at: datetime


class ReviewItemDetail(BaseModel):
    id: int
    status: ReviewStatus
    reason: RuleApplied
    created_at: datetime
    resolved_at: datetime | None
    resolved_by: str | None
    question: str
    answer: str
    raw_model_answer: str | None
    decision: Decision
    rule_applied: RuleApplied
    confidence: ConfidenceBreakdown
    sources: list[SourceChunk]
    actions: list[ReviewActionOut]


class NewDocumentPayload(BaseModel):
    slug: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)
    category: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)


class ReviewActionRequest(BaseModel):
    action_type: ActionType
    note: str | None = None
    actor: str = "reviewer"
    corrected_answer: str | None = Field(
        default=None,
        description=(
            "Requerido para correct / correct_and_create_document / correct_and_edit_document."
        ),
    )
    new_document: NewDocumentPayload | None = Field(
        default=None, description="Requerido para correct_and_create_document."
    )
    document_id: int | None = Field(
        default=None, description="Requerido para correct_and_edit_document."
    )
    document_content: str | None = Field(
        default=None, description="Requerido para correct_and_edit_document."
    )


class RetestSnapshot(BaseModel):
    answer: str
    decision: Decision
    confidence_score: float
    support: str | None


class RetestResponse(BaseModel):
    before: RetestSnapshot
    after: RetestSnapshot


class DocumentSummary(BaseModel):
    id: int
    slug: str
    title: str
    category: str
    is_active: bool
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentSummary]


class DocumentVersionOut(BaseModel):
    id: int
    content: str
    changed_by: str
    reason: str
    review_item_id: int | None
    created_at: datetime


class DocumentDetail(BaseModel):
    id: int
    slug: str
    title: str
    category: str
    content: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    versions: list[DocumentVersionOut]


class DocumentCreateRequest(BaseModel):
    slug: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)
    category: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)


class DocumentUpdateRequest(BaseModel):
    title: str | None = None
    category: str | None = None
    content: str = Field(min_length=1)
    changed_by: str = "reviewer"
    reason: str = ""
    review_item_id: int | None = None


class KnowledgeGapGroup(BaseModel):
    representative_question: str = Field(
        description="La pregunta más corta del grupo, como formulación representativa."
    )
    count: int
    example_questions: list[str]
    query_ids: list[int] = Field(
        description="Para poder revisar cada caso individual si hace falta."
    )
