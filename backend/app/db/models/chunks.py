import datetime as dt

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.config import get_settings
from app.db.base import Base
from app.db.models.documents import Document


class Chunk(Base):
    """Un fragmento de un documento, con su embedding.

    `content_tsv` (para full-text) es una columna generada por Postgres
    (ver la migración) — no se mapea aquí porque nadie le escribe valores
    desde Python, y el retrieval híbrido la consulta con SQL crudo.
    """

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_index: Mapped[int] = mapped_column()
    heading_path: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    token_count: Mapped[int] = mapped_column()
    embedding: Mapped[list[float]] = mapped_column(Vector(get_settings().embedding_dimensions))
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    document: Mapped[Document] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_chunks_document_chunk_index"),
        Index("ix_chunks_document_id", "document_id"),
    )
