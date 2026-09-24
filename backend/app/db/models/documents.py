import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.chunks import Chunk


class Document(Base):
    """Un documento de la base de conocimiento. El Markdown en knowledge_base/
    es solo la fuente para la primera ingesta: después de eso, esta tabla es
    la fuente de verdad, porque el revisor puede editar documentos desde la
    consola (Fase 3).
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="Chunk.chunk_index"
    )
    versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentVersion(Base):
    """Historial de ediciones hechas desde la consola de revisión (Fase 3).
    No se escribe nada aquí durante la ingesta inicial desde Markdown —
    solo cuando un revisor corrige o crea un documento a partir de un caso.
    """

    __tablename__ = "document_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text)
    changed_by: Mapped[str] = mapped_column(String(200))
    reason: Mapped[str] = mapped_column(Text)
    # FK real a review_items se agrega en la migración de la Fase 3 (esa
    # tabla todavía no existe); por ahora es un entero suelto.
    review_item_id: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    document: Mapped["Document"] = relationship(back_populates="versions")
