"""CRUD de documentos de la base de conocimiento para la consola de
revisión. Crear/editar siempre re-ingieren (chunking + embeddings) en la
misma request — no hay un estado "pendiente de re-ingesta" async porque
`ingest_document` corre síncrono y la respuesta ya refleja el resultado.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.review_schemas import (
    DocumentCreateRequest,
    DocumentDetail,
    DocumentListResponse,
    DocumentSummary,
    DocumentUpdateRequest,
    DocumentVersionOut,
)
from app.core.security import require_review_console_token
from app.db.models.documents import Document
from app.db.session import get_db
from app.rag.embeddings import EmbeddingProvider, get_embedding_provider
from app.review.documents import (
    DocumentNotFoundError,
    DuplicateSlugError,
    create_document,
    get_document,
    list_documents,
    update_document,
)

router = APIRouter(prefix="/documents", dependencies=[Depends(require_review_console_token)])


def _to_detail(document: Document) -> DocumentDetail:
    versions = sorted(document.versions, key=lambda v: v.created_at, reverse=True)
    return DocumentDetail(
        id=document.id,
        slug=document.slug,
        title=document.title,
        category=document.category,
        content=document.content,
        is_active=document.is_active,
        created_at=document.created_at,
        updated_at=document.updated_at,
        versions=[
            DocumentVersionOut(
                id=v.id,
                content=v.content,
                changed_by=v.changed_by,
                reason=v.reason,
                review_item_id=v.review_item_id,
                created_at=v.created_at,
            )
            for v in versions
        ],
    )


@router.get("", response_model=DocumentListResponse)
def get_documents(
    q: str | None = None, category: str | None = None, db: Session = Depends(get_db)
) -> DocumentListResponse:
    documents = list_documents(db, q=q, category=category)
    return DocumentListResponse(
        items=[
            DocumentSummary(
                id=d.id,
                slug=d.slug,
                title=d.title,
                category=d.category,
                is_active=d.is_active,
                updated_at=d.updated_at,
            )
            for d in documents
        ]
    )


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document_detail(document_id: int, db: Session = Depends(get_db)) -> DocumentDetail:
    try:
        document = get_document(db, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_detail(document)


@router.post("", response_model=DocumentDetail, status_code=201)
def post_document(
    body: DocumentCreateRequest,
    db: Session = Depends(get_db),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
) -> DocumentDetail:
    try:
        document = create_document(
            db,
            embedding_provider,
            slug=body.slug,
            title=body.title,
            category=body.category,
            content=body.content,
        )
    except DuplicateSlugError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_detail(document)


@router.put("/{document_id}", response_model=DocumentDetail)
def put_document(
    document_id: int,
    body: DocumentUpdateRequest,
    db: Session = Depends(get_db),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
) -> DocumentDetail:
    try:
        document = update_document(
            db,
            embedding_provider,
            document_id=document_id,
            content=body.content,
            changed_by=body.changed_by,
            reason=body.reason,
            title=body.title,
            category=body.category,
            review_item_id=body.review_item_id,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_detail(document)
