from dataclasses import dataclass
from typing import Literal

Support = Literal["full", "partial", "none"]


@dataclass
class ConfidenceSignals:
    """Todo lo que entra en la decisión de enrutamiento, junto en un solo
    lugar para poder guardarlo y auditarlo completo por cada consulta (ver
    `Query` en app/db/models/queries.py).
    """

    retrieval_score: float  # similitud coseno cruda del mejor chunk (0-1)
    retrieval_margin: float  # diferencia cruda entre el 1er y 2do mejor chunk (0-1)
    support: Support | None  # None si la generación falló antes de producir una respuesta
    needs_human: bool
    citation_valid: bool
    generation_error: str | None
