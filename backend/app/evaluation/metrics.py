"""Métricas puras del harness de evaluación — sin base de datos ni API,
para poder testearlas igual que RRF o el puntaje de confianza.
"""

from __future__ import annotations

from dataclasses import dataclass


def compute_recall_at_k(expected_doc_slugs: list[str], actual_doc_slugs: list[str]) -> float | None:
    """Fracción de `expected_doc_slugs` que aparece entre los documentos
    recuperados. `None` (no `0.0`) cuando el caso no tiene documentos
    esperados que medir — p. ej. una pregunta que debe escalar sin tocar
    la base de conocimiento, o una que a propósito no tiene soporte. Un
    `0.0` ahí ensuciaría el promedio con casos donde "no encontrar nada"
    es justo el comportamiento correcto.
    """
    if not expected_doc_slugs:
        return None
    found = sum(1 for slug in expected_doc_slugs if slug in actual_doc_slugs)
    return found / len(expected_doc_slugs)


def is_routing_correct(should_escalate: bool, decision: str) -> bool:
    """Lo único que este harness exige del enrutamiento: un caso marcado
    `should_escalate` (reclamo, problema de pedido/pago) DEBE terminar en
    "escalate", y uno que no lo es NUNCA debe escalar por error. No exige
    coincidir el resto de la escala (direct/warn/review) porque esos tres
    dependen de umbrales que se están calibrando — escalar mal (o no
    escalar cuando debía) es el único error de enrutamiento que de verdad
    importa para la demo: un reclamo real que cae en "direct" es el peor
    caso posible del sistema.
    """
    if should_escalate:
        return decision == "escalate"
    return decision != "escalate"


@dataclass
class CaseMetrics:
    recall_at_k: float | None
    routing_correct: bool
    judge_verdict: str | None


def aggregate_metrics(
    cases: list[CaseMetrics], total_cost_usd: float, total_latency_ms: int
) -> dict:
    """Resumen de una corrida completa. Cada promedio se calcula solo sobre
    los casos donde la métrica aplica (ver `compute_recall_at_k` y
    `judge_verdict=None` en casos should_escalate) — dividir por el total
    de casos subestimaría el resultado en corridas con muchos casos de
    escalamiento, que no tienen ni recall ni veredicto del juez.
    """
    n = len(cases)
    recalls = [c.recall_at_k for c in cases if c.recall_at_k is not None]
    verdicts = [c.judge_verdict for c in cases if c.judge_verdict is not None]
    routing_correct_count = sum(1 for c in cases if c.routing_correct)

    return {
        "total_cases": n,
        "routing_accuracy": routing_correct_count / n if n else None,
        "mean_recall_at_k": sum(recalls) / len(recalls) if recalls else None,
        "recall_cases_evaluated": len(recalls),
        "judge_correct_rate": (
            sum(1 for v in verdicts if v == "correct") / len(verdicts) if verdicts else None
        ),
        "judge_cases_evaluated": len(verdicts),
        "total_cost_usd": round(total_cost_usd, 6),
        "mean_latency_ms": total_latency_ms / n if n else None,
    }
