"""Esquemas Pydantic del dashboard de la consola (Fase 7)."""

from datetime import datetime

from pydantic import BaseModel


class DashboardSummaryOut(BaseModel):
    total_queries: int
    decision_counts: dict[str, int]
    avg_confidence_score: float | None
    avg_latency_ms: float | None
    total_cost_usd: float
    pending_review_count: int
    document_count: int


class EvaluationRunOut(BaseModel):
    id: int
    created_at: datetime
    metrics: dict
    config_snapshot: dict


class EvaluationRunListResponse(BaseModel):
    runs: list[EvaluationRunOut]
