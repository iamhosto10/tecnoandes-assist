"""Puntaje de confianza, de 0 a 100.

Combinación ponderada de tres señales normalizadas: qué tan bueno fue el
mejor chunk recuperado, qué tan claramente le ganó al segundo, y qué tan
respaldada dice el propio modelo que está la respuesta. Los pesos y los
"valores de referencia" usados para normalizar retrieval_score/margin son
una heurística inicial (documentada en `.env.example`) que se recalibra
con `make eval` (Fase 6) — no se presentan como si ya fueran óptimos.

Se devuelve el desglose completo (no solo el total) porque el "modo
transparente" del chat (Fase 4) y la vista de caso de la consola (Fase 5)
necesitan mostrar de qué está hecho el puntaje, no solo el número final —
esa explicabilidad es el punto central del sistema de confianza.

`needs_human` y `citation_valid` NO entran en esta fórmula: son compuertas
duras que deciden el enrutamiento directamente en `rules.py`, no señales
que se promedien con las demás (ver CLAUDE.md).
"""

from dataclasses import dataclass

from app.confidence.signals import ConfidenceSignals
from app.core.config import get_settings

_SUPPORT_VALUE = {"full": 1.0, "partial": 0.5, "none": 0.0}


@dataclass
class ScoreComponent:
    weight: float
    normalized_value: float  # 0-1, después de aplicar floor/ceiling
    points: float  # weight * normalized_value * 100, lo que aporta al total


@dataclass
class ConfidenceScoreBreakdown:
    retrieval_score: ScoreComponent
    retrieval_margin: ScoreComponent
    support: ScoreComponent
    total: float


def _normalize(value: float, floor: float, ceiling: float) -> float:
    if ceiling <= floor:
        return 0.0
    return max(0.0, min(1.0, (value - floor) / (ceiling - floor)))


def compute_confidence_score(signals: ConfidenceSignals) -> ConfidenceScoreBreakdown:
    settings = get_settings()

    normalized_retrieval = _normalize(
        signals.retrieval_score,
        settings.confidence_retrieval_floor,
        settings.confidence_retrieval_ceiling,
    )
    normalized_margin = _normalize(
        signals.retrieval_margin, 0.0, settings.confidence_margin_ceiling
    )
    support_value = _SUPPORT_VALUE.get(signals.support, 0.0)

    retrieval_component = ScoreComponent(
        weight=settings.confidence_weight_retrieval_score,
        normalized_value=normalized_retrieval,
        points=round(settings.confidence_weight_retrieval_score * normalized_retrieval * 100, 2),
    )
    margin_component = ScoreComponent(
        weight=settings.confidence_weight_retrieval_margin,
        normalized_value=normalized_margin,
        points=round(settings.confidence_weight_retrieval_margin * normalized_margin * 100, 2),
    )
    support_component = ScoreComponent(
        weight=settings.confidence_weight_support,
        normalized_value=support_value,
        points=round(settings.confidence_weight_support * support_value * 100, 2),
    )

    total = round(
        retrieval_component.points + margin_component.points + support_component.points, 2
    )

    return ConfidenceScoreBreakdown(
        retrieval_score=retrieval_component,
        retrieval_margin=margin_component,
        support=support_component,
        total=total,
    )
