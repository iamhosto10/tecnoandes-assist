"""Esquemas Pydantic del contrato HTTP — separados de los modelos de
SQLAlchemy para no acoplar la forma de la API al esquema de la base de
datos (uno puede cambiar sin forzar el otro).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from app.confidence.rules import Decision

if TYPE_CHECKING:
    from app.confidence.scoring import ConfidenceScoreBreakdown
    from app.confidence.signals import ConfidenceSignals

# Los 8 valores que puede devolver decide_routing() (app/confidence/rules.py);
# se declara acá como Literal (no str) para que el OpenAPI genere un enum de
# verdad y el cliente TS (packages/api-client) no reciba un `string` genérico.
RuleApplied = Literal[
    "needs_human",
    "generation_error",
    "invalid_citation",
    "no_support",
    "partial_support",
    "low_score",
    "mid_score",
    "high_score",
]


class AskRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=2000,
        description="Pregunta del cliente, en español.",
        examples=["¿Hay sede de TecnoAndes en Cali?"],
    )


class SourceChunk(BaseModel):
    chunk_id: int
    document_slug: str = Field(description="Slug del documento fuente en knowledge_base/.")
    document_title: str
    heading_path: str = Field(description="Breadcrumb de encabezados dentro del documento.")
    content: str
    vector_score: float = Field(
        description="Similitud coseno cruda (0-1) del retrieval vectorial."
    )
    fulltext_score: float = Field(description="ts_rank crudo del retrieval de texto completo.")
    rrf_score: float = Field(description="Puntaje fusionado por Reciprocal Rank Fusion.")
    cited: bool = Field(description="Si el modelo citó este chunk en `cited_chunk_ids`.")


class ScoreComponentOut(BaseModel):
    weight: float = Field(description="Peso de esta señal en el puntaje final (0-1).")
    normalized_value: float = Field(
        description="Valor de la señal normalizado a 0-1 (después de floor/ceiling)."
    )
    points: float = Field(description="Cuánto aporta esta señal al puntaje 0-100.")


class ScoreBreakdown(BaseModel):
    retrieval_score: ScoreComponentOut
    retrieval_margin: ScoreComponentOut
    support: ScoreComponentOut


class ConfidenceBreakdown(BaseModel):
    retrieval_score: float = Field(
        description="Similitud coseno cruda del mejor chunk (sin normalizar)."
    )
    retrieval_margin: float = Field(
        description="Diferencia cruda entre el 1er y 2do mejor chunk (sin normalizar)."
    )
    support: str | None = Field(
        description='"full" | "partial" | "none", o null si falló la generación.'
    )
    needs_human: bool
    citation_valid: bool = Field(
        description="Si todos los cited_chunk_ids existían en el contexto entregado al modelo."
    )
    confidence_score: float = Field(
        description="Puntaje ponderado 0-100 (ver app/confidence/scoring.py)."
    )
    score_breakdown: ScoreBreakdown = Field(
        description="Detalle de cuánto aportó cada señal al confidence_score."
    )

    @classmethod
    def from_domain(
        cls, signals: ConfidenceSignals, score: ConfidenceScoreBreakdown
    ) -> ConfidenceBreakdown:
        # Un solo lugar que arma esta respuesta desde los tipos de dominio,
        # para que /ask y /review/items/{id} no dupliquen el mapeo.
        return cls(
            retrieval_score=signals.retrieval_score,
            retrieval_margin=signals.retrieval_margin,
            support=signals.support,
            needs_human=signals.needs_human,
            citation_valid=signals.citation_valid,
            confidence_score=score.total,
            score_breakdown=ScoreBreakdown(
                retrieval_score=ScoreComponentOut(
                    weight=score.retrieval_score.weight,
                    normalized_value=score.retrieval_score.normalized_value,
                    points=score.retrieval_score.points,
                ),
                retrieval_margin=ScoreComponentOut(
                    weight=score.retrieval_margin.weight,
                    normalized_value=score.retrieval_margin.normalized_value,
                    points=score.retrieval_margin.points,
                ),
                support=ScoreComponentOut(
                    weight=score.support.weight,
                    normalized_value=score.support.normalized_value,
                    points=score.support.points,
                ),
            ),
        )


class AskResponse(BaseModel):
    query_id: int = Field(
        description="Id del registro en la tabla `queries`, para auditar el caso."
    )
    answer: str = Field(
        description="Lo que ve el cliente; puede ser un mensaje de respaldo si decision=review."
    )
    decision: Decision = Field(
        description='Resultado del enrutamiento: "direct" | "warn" | "review" | "escalate".',
        examples=["direct"],
    )
    rule_applied: RuleApplied = Field(
        description="Qué regla de app/confidence/rules.py disparó la decisión."
    )
    confidence: ConfidenceBreakdown
    cited_chunk_ids: list[int] = Field(description="Ids de chunks que el modelo dice haber usado.")
    sources: list[SourceChunk] = Field(
        description="Todos los chunks recuperados (no solo los citados)."
    )
    latency_ms: int = Field(description="Tiempo de la llamada al LLM, en milisegundos.")
    input_tokens: int
    output_tokens: int
    cost_usd: float = Field(description="Costo estimado de esta consulta, en USD.")
