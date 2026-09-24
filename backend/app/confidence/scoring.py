"""Puntaje de confianza, de 0 a 100.

Combinación ponderada de tres señales normalizadas: qué tan bueno fue el
mejor chunk recuperado, qué tan claramente le ganó al segundo, y qué tan
respaldada dice el propio modelo que está la respuesta. Los pesos y los
"valores de referencia" usados para normalizar retrieval_score/margin son
una heurística inicial (documentada en `.env.example`) que se recalibra
con `make eval` (Fase 6) — no se presentan como si ya fueran óptimos.

`needs_human` y `citation_valid` NO entran en esta fórmula: son compuertas
duras que deciden el enrutamiento directamente en `rules.py`, no señales
que se promedien con las demás (ver CLAUDE.md).
"""

from app.confidence.signals import ConfidenceSignals
from app.core.config import get_settings

_SUPPORT_VALUE = {"full": 1.0, "partial": 0.5, "none": 0.0}


def _normalize(value: float, floor: float, ceiling: float) -> float:
    if ceiling <= floor:
        return 0.0
    return max(0.0, min(1.0, (value - floor) / (ceiling - floor)))


def compute_confidence_score(signals: ConfidenceSignals) -> float:
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

    weighted = (
        settings.confidence_weight_retrieval_score * normalized_retrieval
        + settings.confidence_weight_retrieval_margin * normalized_margin
        + settings.confidence_weight_support * support_value
    )
    return round(weighted * 100, 2)
