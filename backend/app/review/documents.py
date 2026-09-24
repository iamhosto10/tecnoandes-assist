"""CRUD de documentos de la base de conocimiento para la consola de
revisión. Crear y editar pasan siempre por `ingest_document` (Fase 1):
así la consola nunca puede dejar un documento con chunks/embeddings
desactualizados — guardar y re-ingerir son la misma operación.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.documents import Document
from app.rag.embeddings import EmbeddingProvider
from app.rag.ingestion import ingest_document


class DocumentNotFoundError(ValueError):
    pass


class DuplicateSlugError(ValueError):
    pass


def list_documents(
    session: Session, q: str | None = None, category: str | None = None
) -> list[Document]:
    stmt = select(Document).order_by(Document.title)
    if category is not None:
        stmt = stmt.where(Document.category == category)
    if q:
        stmt = stmt.where(Document.title.ilike(f"%{q}%"))
    return list(session.scalars(stmt).all())


def get_document(session: Session, document_id: int) -> Document:
    document = session.get(Document, document_id)
    if document is None:
        raise DocumentNotFoundError(f"no existe el documento {document_id}")
    return document


def create_document(
    session: Session,
    embedding_provider: EmbeddingProvider,
    slug: str,
    title: str,
    category: str,
    content: str,
) -> Document:
    existing = session.query(Document).filter_by(slug=slug).one_or_none()
    if existing is not None:
        raise DuplicateSlugError(f"ya existe un documento con slug '{slug}'")

    ingest_document(
        session,
        slug=slug,
        title=title,
        category=category,
        content=content,
        embedding_provider=embedding_provider,
    )
    session.commit()
    return session.query(Document).filter_by(slug=slug).one()


def update_document(
    session: Session,
    embedding_provider: EmbeddingProvider,
    document_id: int,
    content: str,
    changed_by: str,
    reason: str,
    title: str | None = None,
    category: str | None = None,
    review_item_id: int | None = None,
) -> Document:
    document = get_document(session, document_id)

    ingest_document(
        session,
        slug=document.slug,
        title=title or document.title,
        category=category or document.category,
        content=content,
        embedding_provider=embedding_provider,
        changed_by=changed_by,
        reason=reason,
        review_item_id=review_item_id,
    )
    session.commit()
    session.refresh(document)
    return document
