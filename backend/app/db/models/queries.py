import datetime as dt

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Query(Base):
    """Un registro inmutable de cada `/ask`: la pregunta, la respuesta que
    vio el cliente, todas las señales de confianza y la decisión de
    enrutamiento. Junto con `document_versions` y (desde la Fase 3)
    `review_actions`, es la fuente de auditoría del sistema — no hay una
    tabla `audit_log` genérica separada (ver la decisión en CLAUDE.md).
    """

    __tablename__ = "queries"

    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(Text)

    # `answer` es lo que efectivamente vio el cliente (puede ser un mensaje
    # de respaldo genérico si la decisión fue "review"); `raw_model_answer`
    # es lo que el modelo devolvió, para poder auditar aunque no se haya
    # mostrado — lo usa el "modo transparente" (Fase 4) y la consola (Fase 5).
    answer: Mapped[str] = mapped_column(Text)
    raw_model_answer: Mapped[str | None] = mapped_column(Text, nullable=True)

    support: Mapped[str | None] = mapped_column(String(10), nullable=True)
    needs_human: Mapped[bool] = mapped_column(Boolean, default=False)
    needs_human_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cited_chunk_ids: Mapped[list[int]] = mapped_column(JSONB, default=list)
    citation_valid: Mapped[bool] = mapped_column(Boolean, default=True)

    retrieval_score: Mapped[float] = mapped_column(Float)
    retrieval_margin: Mapped[float] = mapped_column(Float)
    confidence_score: Mapped[float] = mapped_column(Float)

    decision: Mapped[str] = mapped_column(String(20))
    rule_applied: Mapped[str] = mapped_column(String(50))
    generation_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    latency_ms: Mapped[int] = mapped_column(Integer)
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    cost_usd: Mapped[float] = mapped_column(Float)

    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    retrieved_chunks: Mapped[list["QueryChunk"]] = relationship(
        back_populates="query", cascade="all, delete-orphan", order_by="QueryChunk.rank"
    )


class QueryChunk(Base):
    """Detalle por consulta de qué chunks se recuperaron y con qué puntajes
    — lo que alimenta el "modo transparente" del chat (Fase 4) y la vista
    de caso en la consola de revisión (Fase 5). Tabla `retrieved_chunks`.
    """

    __tablename__ = "retrieved_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    query_id: Mapped[int] = mapped_column(ForeignKey("queries.id", ondelete="CASCADE"))
    chunk_id: Mapped[int] = mapped_column(ForeignKey("chunks.id", ondelete="CASCADE"))
    rank: Mapped[int] = mapped_column(Integer)
    vector_score: Mapped[float] = mapped_column(Float)
    fulltext_score: Mapped[float] = mapped_column(Float)
    rrf_score: Mapped[float] = mapped_column(Float)

    query: Mapped[Query] = relationship(back_populates="retrieved_chunks")
