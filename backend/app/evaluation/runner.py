"""Orquesta una corrida completa de evaluación: por cada `EvaluationCase`,
corre el pipeline real (`run_ask_pipeline`, el mismo que usan `/ask` y
`/review/items/{id}/retest` — Fase 2/3, sin duplicar lógica), lo compara
contra lo esperado, y persiste `EvaluationRun` + `EvaluationResult`.

Vive separado de `scripts/evaluate.py` para poder testearlo con un
cliente de Anthropic simulado (mismo patrón que el resto del proyecto:
la lógica de negocio no vive en el script de CLI).
"""

from __future__ import annotations

import anthropic
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.evaluation import EvaluationCase, EvaluationResult, EvaluationRun
from app.evaluation.judge import judge_answer
from app.evaluation.metrics import (
    CaseMetrics,
    aggregate_metrics,
    compute_recall_at_k,
    is_routing_correct,
)
from app.rag.embeddings import EmbeddingProvider
from app.rag.pipeline import run_ask_pipeline


def _config_snapshot() -> dict:
    # Todo lo que puede cambiar entre corridas y que hace falta para
    # interpretar los resultados después — sin esto, un EvaluationResult de
    # hace tres recalibraciones no se puede comparar de forma justa con uno
    # de hoy (ver CLAUDE.md, decisión de Fase 6).
    settings = get_settings()
    return {
        "anthropic_model": settings.anthropic_model,
        "anthropic_judge_model": settings.anthropic_judge_model,
        "embedding_model": settings.embedding_model,
        "retrieval_top_k": settings.retrieval_top_k,
        "confidence_threshold_low": settings.confidence_threshold_low,
        "confidence_threshold_high": settings.confidence_threshold_high,
        "confidence_weight_retrieval_score": settings.confidence_weight_retrieval_score,
        "confidence_weight_retrieval_margin": settings.confidence_weight_retrieval_margin,
        "confidence_weight_support": settings.confidence_weight_support,
        "confidence_retrieval_floor": settings.confidence_retrieval_floor,
        "confidence_retrieval_ceiling": settings.confidence_retrieval_ceiling,
        "confidence_margin_ceiling": settings.confidence_margin_ceiling,
    }


def _judge_cost_usd(input_tokens: int, output_tokens: int) -> float:
    # Mismos precios configurados que la generación — el juez por defecto
    # corre en el mismo modelo (Haiku 4.5); si se calibra con un juez
    # distinto, el costo mostrado queda subestimado/sobrestimado según la
    # diferencia real de precio (simplificación aceptada, ver CLAUDE.md).
    settings = get_settings()
    cost = (
        input_tokens * settings.anthropic_input_price_per_mtok
        + output_tokens * settings.anthropic_output_price_per_mtok
    ) / 1_000_000
    return round(cost, 8)


def evaluate_case(
    case: EvaluationCase,
    db: Session,
    embedding_provider: EmbeddingProvider,
    anthropic_client: anthropic.Anthropic,
) -> EvaluationResult:
    pipeline_result = run_ask_pipeline(case.question, db, embedding_provider, anthropic_client)

    actual_doc_slugs = [c.document_slug for c in pipeline_result.chunks]
    recall_at_k = compute_recall_at_k(case.expected_doc_slugs, actual_doc_slugs)
    routing_correct = is_routing_correct(case.should_escalate, pipeline_result.routing.decision)

    judge_verdict: str | None = None
    judge_reason: str | None = None
    cost_usd = pipeline_result.generation.cost_usd

    # Solo se juzga la calidad de la respuesta cuando hay una esperada que
    # comparar — un caso should_escalate se evalúa por routing_correct, no
    # por si el mensaje de traspaso a un humano "suena bien".
    if case.expected_answer is not None:
        judge_result = judge_answer(
            case.question, case.expected_answer, pipeline_result.customer_answer, anthropic_client
        )
        judge_verdict = judge_result.verdict
        judge_reason = judge_result.reason
        cost_usd += _judge_cost_usd(judge_result.input_tokens, judge_result.output_tokens)

    return EvaluationResult(
        case_id=case.id,
        actual_answer=pipeline_result.customer_answer,
        actual_doc_slugs=actual_doc_slugs,
        recall_at_k=recall_at_k,
        judge_verdict=judge_verdict,
        judge_reason=judge_reason,
        routing_correct=routing_correct,
        decision=pipeline_result.routing.decision,
        confidence_score=pipeline_result.confidence_score,
        latency_ms=pipeline_result.generation.latency_ms,
        cost_usd=cost_usd,
    )


def run_evaluation(
    cases: list[EvaluationCase],
    db: Session,
    embedding_provider: EmbeddingProvider,
    anthropic_client: anthropic.Anthropic,
) -> EvaluationRun:
    results = [evaluate_case(case, db, embedding_provider, anthropic_client) for case in cases]

    metrics = aggregate_metrics(
        [
            CaseMetrics(
                recall_at_k=r.recall_at_k,
                routing_correct=r.routing_correct,
                judge_verdict=r.judge_verdict,
            )
            for r in results
        ],
        total_cost_usd=sum(r.cost_usd for r in results),
        total_latency_ms=sum(r.latency_ms for r in results),
    )

    run = EvaluationRun(config_snapshot=_config_snapshot(), metrics=metrics, results=results)
    db.add(run)
    db.flush()
    return run
