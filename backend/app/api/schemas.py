"""Esquemas Pydantic del contrato HTTP — separados de los modelos de
SQLAlchemy para no acoplar la forma de la API al esquema de la base de
datos (uno puede cambiar sin forzar el otro).
"""

from pydantic import BaseModel, Field


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


class AskResponse(BaseModel):
    query_id: int = Field(
        description="Id del registro en la tabla `queries`, para auditar el caso."
    )
    answer: str = Field(
        description="Lo que ve el cliente; puede ser un mensaje de respaldo si decision=review."
    )
    decision: str = Field(
        description='Resultado del enrutamiento: "direct" | "warn" | "review" | "escalate".',
        examples=["direct"],
    )
    rule_applied: str = Field(
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
