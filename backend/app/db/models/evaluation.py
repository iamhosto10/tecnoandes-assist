import datetime as dt

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class EvaluationCase(Base):
    """Una pregunta con su respuesta esperada, para medir el pipeline
    completo (retrieval + generación + enrutamiento) de punta a punta.

    `should_escalate` marca casos donde la pregunta ES un reclamo/problema
    de pedido o pago (debe disparar la regla `needs_human` y enrutar a
    "escalate") — no es lo mismo que "no se puede responder con la base de
    conocimiento" (`support=none`, enruta a "review"); ver `routing_correct`
    en `app/evaluation/metrics.py`. `expected_answer` es null para esos
    casos: ahí se evalúa que escaló, no la calidad de una respuesta.
    `origin` distingue el set semilla (`eval/seed.jsonl`) de casos reales
    que un revisor promovió desde la cola (Fase 7), sin mezclar ambas
    fuentes en tablas separadas.
    """

    __tablename__ = "evaluation_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    expected_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_doc_slugs: Mapped[list[str]] = mapped_column(JSONB, default=list)
    should_escalate: Mapped[bool] = mapped_column(Boolean, default=False)
    category: Mapped[str] = mapped_column(String(50))
    origin: Mapped[str] = mapped_column(String(20), default="seed")
    source_review_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("review_items.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())


class EvaluationRun(Base):
    """Una corrida de `make eval`. `config_snapshot` congela los pesos,
    umbrales, top_k y el modelo vigentes en el momento — así un `EvaluationResult`
    sigue siendo interpretable después de recalibrar (ver CLAUDE.md, decisión
    de Fase 6), sin tener que cruzarlo contra el historial de `.env`.
    """

    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    config_snapshot: Mapped[dict] = mapped_column(JSONB)
    metrics: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    results: Mapped[list["EvaluationResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class EvaluationResult(Base):
    """El resultado de un caso dentro de una corrida: lo que contestó el
    pipeline, si el retrieval trajo el documento esperado, si enrutó
    correctamente, y el veredicto de un LLM juez sobre la calidad de la
    respuesta (solo para casos con `expected_answer`; ver `app/evaluation/judge.py`).
    """

    __tablename__ = "evaluation_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("evaluation_runs.id", ondelete="CASCADE"))
    case_id: Mapped[int] = mapped_column(ForeignKey("evaluation_cases.id", ondelete="CASCADE"))

    actual_answer: Mapped[str] = mapped_column(Text)
    actual_doc_slugs: Mapped[list[str]] = mapped_column(JSONB, default=list)
    # None cuando el caso no tiene `expected_doc_slugs` que medir (p. ej. casos should_escalate).
    recall_at_k: Mapped[float | None] = mapped_column(Float, nullable=True)

    # None cuando el caso no tiene `expected_answer` que juzgar (should_escalate=true).
    judge_verdict: Mapped[str | None] = mapped_column(String(20), nullable=True)
    judge_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    routing_correct: Mapped[bool] = mapped_column(Boolean)
    decision: Mapped[str] = mapped_column(String(20))
    confidence_score: Mapped[float] = mapped_column(Float)
    latency_ms: Mapped[int] = mapped_column(Integer)
    cost_usd: Mapped[float] = mapped_column(Float)

    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    run: Mapped[EvaluationRun] = relationship(back_populates="results")
    case: Mapped[EvaluationCase] = relationship()
