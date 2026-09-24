"""Aplica una acción del revisor sobre un caso de la cola: aprobar,
corregir (con o sin tocar la base de conocimiento), escalar o descartar.
Las acciones que tocan documentos reusan `ingest_document` — la misma
función de la Fase 1 — para no duplicar la lógica de chunking/embeddings
ni la de versionado.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models.documents import Document
from app.db.models.review import ReviewAction, ReviewItem
from app.rag.embeddings import EmbeddingProvider
from app.rag.ingestion import ingest_document

ACTION_TYPES = (
    "approve",
    "correct",
    "correct_and_create_document",
    "correct_and_edit_document",
    "escalate",
    "discard",
)

_STATUS_BY_ACTION = {
    "approve": "approved",
    "correct": "corrected",
    "correct_and_create_document": "corrected",
    "correct_and_edit_document": "corrected",
    "escalate": "escalated",
    "discard": "discarded",
}


class ReviewActionError(ValueError):
    """Datos insuficientes o inconsistentes para aplicar la acción."""


@dataclass
class NewDocumentInput:
    slug: str
    title: str
    category: str
    content: str


def apply_review_action(
    session: Session,
    review_item: ReviewItem,
    embedding_provider: EmbeddingProvider,
    action_type: str,
    actor: str,
    note: str | None = None,
    corrected_answer: str | None = None,
    new_document: NewDocumentInput | None = None,
    document_id: int | None = None,
    document_content: str | None = None,
) -> ReviewAction:
    if action_type not in ACTION_TYPES:
        raise ReviewActionError(f"action_type inválido: {action_type}")

    if action_type in ("correct", "correct_and_create_document", "correct_and_edit_document"):
        if not corrected_answer:
            raise ReviewActionError("corrected_answer es requerido para esta acción")

    if action_type == "escalate" and not note:
        raise ReviewActionError("note es requerido para escalar")

    document_id_for_action: int | None = None

    if action_type == "correct_and_create_document":
        if new_document is None:
            raise ReviewActionError("new_document es requerido")
        existing = session.query(Document).filter_by(slug=new_document.slug).one_or_none()
        if existing is not None:
            raise ReviewActionError(f"ya existe un documento con slug '{new_document.slug}'")
        ingest_document(
            session,
            slug=new_document.slug,
            title=new_document.title,
            category=new_document.category,
            content=new_document.content,
            embedding_provider=embedding_provider,
        )
        session.flush()
        created = session.query(Document).filter_by(slug=new_document.slug).one()
        document_id_for_action = created.id

    elif action_type == "correct_and_edit_document":
        if document_id is None or not document_content:
            raise ReviewActionError("document_id y document_content son requeridos")
        document = session.get(Document, document_id)
        if document is None:
            raise ReviewActionError(f"no existe el documento {document_id}")
        ingest_document(
            session,
            slug=document.slug,
            title=document.title,
            category=document.category,
            content=document_content,
            embedding_provider=embedding_provider,
            changed_by=actor,
            reason=note or "Corrección desde revisión",
            review_item_id=review_item.id,
        )
        document_id_for_action = document.id

    review_item.status = _STATUS_BY_ACTION[action_type]
    review_item.resolved_at = dt.datetime.now(dt.UTC)
    review_item.resolved_by = actor

    # La corrección del revisor reemplaza la respuesta "oficial" del caso;
    # `raw_model_answer` no se toca, sigue siendo lo que el modelo escribió.
    if corrected_answer is not None:
        review_item.query.answer = corrected_answer

    action = ReviewAction(
        review_item_id=review_item.id,
        action_type=action_type,
        note=note,
        actor=actor,
        document_id=document_id_for_action,
    )
    session.add(action)
    session.flush()
    return action
