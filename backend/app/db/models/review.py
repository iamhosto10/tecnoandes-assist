import datetime as dt

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base
from app.db.models.queries import Query


class ReviewItem(Base):
    """Un caso en la cola de revisión. Se crea automáticamente cada vez que
    `/ask` decide algo distinto de "direct" (ver app/rag/pipeline.py) —
    `reason` es el mismo `rule_applied` de la Query que lo originó, así no
    se inventa una segunda taxonomía de motivos.
    """

    __tablename__ = "review_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    query_id: Mapped[int] = mapped_column(ForeignKey("queries.id", ondelete="CASCADE"))
    # pending -> approved | corrected | escalated | discarded
    status: Mapped[str] = mapped_column(String(20), default="pending")
    reason: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    resolved_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(200), nullable=True)

    query: Mapped[Query] = relationship()
    actions: Mapped[list["ReviewAction"]] = relationship(
        back_populates="review_item",
        cascade="all, delete-orphan",
        order_by="ReviewAction.created_at",
    )


class ReviewAction(Base):
    """Historial de acciones del revisor sobre un caso — junto con `queries`
    y `document_versions`, es la auditoría del sistema (no hay una tabla
    `audit_log` genérica; ver la decisión en CLAUDE.md).
    """

    __tablename__ = "review_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    review_item_id: Mapped[int] = mapped_column(ForeignKey("review_items.id", ondelete="CASCADE"))
    action_type: Mapped[str] = mapped_column(String(40))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str] = mapped_column(String(200))
    # Qué documento tocó esta acción (crear o editar), si aplica — para
    # trazar "este documento cambió por este caso de revisión" sin agregar
    # una FK de procedencia en `documents`.
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    review_item: Mapped[ReviewItem] = relationship(back_populates="actions")
