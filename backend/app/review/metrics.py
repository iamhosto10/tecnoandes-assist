"""Agregados para el dashboard de la consola (Fase 7): distribución de
decisiones, costo/latencia, tamaño de la cola y corridas de evaluación
recientes. Separado del router para poder testear las consultas sin HTTP,
mismo patrón que `app/review/queue.py` y `app/review/gaps.py`.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.documents import Document
from app.db.models.evaluation import EvaluationRun
from app.db.models.queries import Query
from app.db.models.review import ReviewItem


@dataclass
class DashboardSummary:
    total_queries: int
    decision_counts: dict[str, int]
    avg_confidence_score: float | None
    avg_latency_ms: float | None
    total_cost_usd: float
    pending_review_count: int
    document_count: int


def get_dashboard_summary(session: Session) -> DashboardSummary:
    total_queries = session.scalar(select(func.count()).select_from(Query)) or 0

    decision_rows = session.execute(
        select(Query.decision, func.count()).group_by(Query.decision)
    ).all()
    decision_counts = {decision: count for decision, count in decision_rows}

    avg_confidence_score = session.scalar(select(func.avg(Query.confidence_score)))
    avg_latency_ms = session.scalar(select(func.avg(Query.latency_ms)))
    total_cost_usd = session.scalar(select(func.coalesce(func.sum(Query.cost_usd), 0.0))) or 0.0

    pending_review_count = (
        session.scalar(
            select(func.count()).select_from(ReviewItem).where(ReviewItem.status == "pending")
        )
        or 0
    )
    document_count = (
        session.scalar(
            select(func.count()).select_from(Document).where(Document.is_active)
        )
        or 0
    )

    return DashboardSummary(
        total_queries=total_queries,
        decision_counts=decision_counts,
        avg_confidence_score=(
            float(avg_confidence_score) if avg_confidence_score is not None else None
        ),
        avg_latency_ms=float(avg_latency_ms) if avg_latency_ms is not None else None,
        total_cost_usd=round(float(total_cost_usd), 6),
        pending_review_count=pending_review_count,
        document_count=document_count,
    )


def list_evaluation_runs(session: Session, limit: int = 20) -> list[EvaluationRun]:
    stmt = select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(limit)
    return list(session.scalars(stmt).all())
