"""Reglas de enrutamiento: la PRIMERA que se cumple gana. El orden es
intencional y viene directo del diseño del sistema — moverlo cambia el
comportamiento, así que cualquier ajuste futuro debe pasar por acá, no
por parchar el resultado en otro lado.
"""

from dataclasses import dataclass
from typing import Literal

from app.confidence.signals import ConfidenceSignals
from app.core.config import get_settings

Decision = Literal["escalate", "review", "warn", "direct"]


@dataclass
class RoutingResult:
    decision: Decision
    rule: str  # identificador corto de qué regla disparó, para el audit


def decide_routing(signals: ConfidenceSignals, confidence_score: float) -> RoutingResult:
    settings = get_settings()

    # 1. Un reclamo, un problema de pedido/pago, o el cliente pidió un
    #    humano: se escala sin mirar nada más.
    if signals.needs_human:
        return RoutingResult("escalate", "needs_human")

    # 2. No hay una respuesta del modelo en la que se pueda confiar: falló
    #    la llamada, la salida no pasó la validación, o citó chunks que no
    #    estaban en el contexto que se le dio.
    if signals.generation_error is not None:
        return RoutingResult("review", "generation_error")
    if not signals.citation_valid:
        return RoutingResult("review", "invalid_citation")

    # 3-4. El propio modelo reporta qué tanto lo respalda el contexto.
    #    "none" nunca se muestra directo — así se alimentan las brechas de
    #    conocimiento (Fase 5). "partial" sí se muestra, pero con advertencia.
    if signals.support == "none":
        return RoutingResult("review", "no_support")
    if signals.support == "partial":
        return RoutingResult("warn", "partial_support")

    # 5-7. A esta altura support es "full": el puntaje ponderado decide.
    if confidence_score < settings.confidence_threshold_low:
        return RoutingResult("review", "low_score")
    if confidence_score < settings.confidence_threshold_high:
        return RoutingResult("warn", "mid_score")
    return RoutingResult("direct", "high_score")
