"""Unitarios de las métricas puras del harness de evaluación — sin base
de datos ni API, mismo patrón que test_rrf.py y test_confidence_scoring.py.
"""

from app.evaluation.metrics import (
    CaseMetrics,
    aggregate_metrics,
    compute_recall_at_k,
    is_routing_correct,
)


def test_recall_at_k_full_match():
    assert compute_recall_at_k(["politica-envios"], ["politica-envios", "faq-general"]) == 1.0


def test_recall_at_k_partial_match():
    assert compute_recall_at_k(["a", "b"], ["a", "c"]) == 0.5


def test_recall_at_k_no_match():
    assert compute_recall_at_k(["politica-envios"], ["faq-general"]) == 0.0


def test_recall_at_k_none_when_no_expected_docs():
    # Un caso sin documentos esperados (p. ej. debería escalar, o a
    # propósito no tiene soporte) no cuenta como un fallo de recall.
    assert compute_recall_at_k([], ["faq-general"]) is None


def test_routing_correct_when_should_escalate_and_did():
    assert is_routing_correct(should_escalate=True, decision="escalate") is True


def test_routing_incorrect_when_should_escalate_but_didnt():
    assert is_routing_correct(should_escalate=True, decision="direct") is False


def test_routing_correct_when_should_not_escalate_and_didnt():
    assert is_routing_correct(should_escalate=False, decision="warn") is True


def test_routing_incorrect_when_escalated_by_mistake():
    assert is_routing_correct(should_escalate=False, decision="escalate") is False


def test_aggregate_metrics_averages_only_over_applicable_cases():
    cases = [
        CaseMetrics(recall_at_k=1.0, routing_correct=True, judge_verdict="correct"),
        CaseMetrics(recall_at_k=0.5, routing_correct=True, judge_verdict="incorrect"),
        # Caso should_escalate: sin recall ni veredicto del juez que promediar.
        CaseMetrics(recall_at_k=None, routing_correct=True, judge_verdict=None),
    ]

    metrics = aggregate_metrics(cases, total_cost_usd=0.01, total_latency_ms=300)

    assert metrics["total_cases"] == 3
    assert metrics["routing_accuracy"] == 1.0
    assert metrics["mean_recall_at_k"] == 0.75
    assert metrics["recall_cases_evaluated"] == 2
    assert metrics["judge_correct_rate"] == 0.5
    assert metrics["judge_cases_evaluated"] == 2
    assert metrics["total_cost_usd"] == 0.01
    assert metrics["mean_latency_ms"] == 100.0


def test_aggregate_metrics_handles_empty_run():
    metrics = aggregate_metrics([], total_cost_usd=0.0, total_latency_ms=0)

    assert metrics["total_cases"] == 0
    assert metrics["routing_accuracy"] is None
    assert metrics["mean_recall_at_k"] is None
    assert metrics["judge_correct_rate"] is None
    assert metrics["mean_latency_ms"] is None
