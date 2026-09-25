"""Endpoints del dashboard de la consola de revisión (Fase 7): un resumen
general de la operación y el historial de corridas de `make eval`.
Protegidos con el token de la consola, igual que /review y /documents —
no es información que deba ver el chat público.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.metrics_schemas import DashboardSummaryOut, EvaluationRunListResponse, EvaluationRunOut
from app.core.security import require_review_console_token
from app.db.session import get_db
from app.review.metrics import get_dashboard_summary, list_evaluation_runs

router = APIRouter(prefix="/metrics", dependencies=[Depends(require_review_console_token)])


@router.get("/summary", response_model=DashboardSummaryOut)
def read_summary(db: Session = Depends(get_db)) -> DashboardSummaryOut:
    summary = get_dashboard_summary(db)
    return DashboardSummaryOut(
        total_queries=summary.total_queries,
        decision_counts=summary.decision_counts,
        avg_confidence_score=summary.avg_confidence_score,
        avg_latency_ms=summary.avg_latency_ms,
        total_cost_usd=summary.total_cost_usd,
        pending_review_count=summary.pending_review_count,
        document_count=summary.document_count,
    )


@router.get("/evaluation-runs", response_model=EvaluationRunListResponse)
def read_evaluation_runs(db: Session = Depends(get_db)) -> EvaluationRunListResponse:
    runs = list_evaluation_runs(db)
    return EvaluationRunListResponse(
        runs=[
            EvaluationRunOut(
                id=r.id,
                created_at=r.created_at,
                metrics=r.metrics,
                config_snapshot=r.config_snapshot,
            )
            for r in runs
        ]
    )
