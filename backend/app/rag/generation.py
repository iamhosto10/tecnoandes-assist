"""Generación de la respuesta: tool use FORZADO contra `submit_answer`, en
vez de pedirle al modelo que devuelva JSON en el texto. Con `tool_choice`
fijo y `strict: true` en el schema, la API garantiza que, si el modelo
responde, `tool_use.input` cumple el schema exactamente — igual se valida
con Pydantic por una segunda capa de seguridad (y porque es lo que pide
el diseño: "valida la salida con Pydantic").

El cliente nunca debe ver un error técnico: cualquier falla (timeout,
rate limit, salida inválida, cita inválida) se refleja en `error` y el
llamador (app/api/ask.py) decide qué mostrarle al cliente en su lugar.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal

import anthropic
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.rag.prompts import SYSTEM_PROMPT
from app.rag.retrieval import RetrievedChunk

SUBMIT_ANSWER_TOOL = {
    "name": "submit_answer",
    "description": (
        "Entrega la respuesta final para el cliente junto con las señales de "
        "confianza sobre esa respuesta."
    ),
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "answer": {
                "type": "string",
                "description": "La respuesta al cliente, en español, breve y clara.",
            },
            "support": {
                "type": "string",
                "enum": ["full", "partial", "none"],
                "description": "Qué tanto respalda el contexto la respuesta.",
            },
            "cited_chunk_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Ids de los chunks del contexto usados para responder.",
            },
            "needs_human": {
                "type": "boolean",
                "description": (
                    "True si hay un reclamo, un problema de pedido/pago, o se pide un humano."
                ),
            },
            "needs_human_reason": {
                "type": ["string", "null"],
                "description": "Motivo breve si needs_human es true; null si no aplica.",
            },
        },
        "required": [
            "answer",
            "support",
            "cited_chunk_ids",
            "needs_human",
            "needs_human_reason",
        ],
        "additionalProperties": False,
    },
}


class SubmitAnswerInput(BaseModel):
    answer: str
    support: Literal["full", "partial", "none"]
    cited_chunk_ids: list[int]
    needs_human: bool
    needs_human_reason: str | None = None


@dataclass
class GenerationResult:
    answer: str | None
    support: Literal["full", "partial", "none"] | None
    cited_chunk_ids: list[int] = field(default_factory=list)
    needs_human: bool = False
    needs_human_reason: str | None = None
    citation_valid: bool = False
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    error: str | None = None  # None si la generación fue válida de punta a punta


@lru_cache
def get_anthropic_client() -> anthropic.Anthropic:
    # Lee ANTHROPIC_API_KEY del entorno; ver core/config.py para el resto
    # de la configuración (modelo, precios).
    return anthropic.Anthropic()


def _build_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(no se encontró contenido relevante en la base de conocimiento)"
    parts = [
        f"[chunk {c.chunk_id}] {c.document_title} > {c.heading_path}\n{c.content}"
        for c in chunks
    ]
    return "\n\n---\n\n".join(parts)


def _estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    settings = get_settings()
    cost = (
        input_tokens * settings.anthropic_input_price_per_mtok
        + output_tokens * settings.anthropic_output_price_per_mtok
    ) / 1_000_000
    return round(cost, 8)


def generate_answer(
    question: str,
    chunks: list[RetrievedChunk],
    client: anthropic.Anthropic,
) -> GenerationResult:
    settings = get_settings()
    context = _build_context(chunks)
    valid_chunk_ids = {c.chunk_id for c in chunks}

    start = time.perf_counter()
    try:
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=[SUBMIT_ANSWER_TOOL],
            tool_choice={"type": "tool", "name": "submit_answer"},
            messages=[
                {
                    "role": "user",
                    "content": f"Contexto:\n\n{context}\n\nPregunta del cliente: {question}",
                }
            ],
        )
    except anthropic.APIError as exc:
        return GenerationResult(
            answer=None,
            support=None,
            latency_ms=int((time.perf_counter() - start) * 1000),
            error=f"anthropic_api_error: {exc}",
        )
    except TypeError as exc:
        # Con ANTHROPIC_API_KEY vacía, el SDK no lanza anthropic.APIError
        # (una anthropic.AuthenticationError normal) sino un TypeError plano
        # al armar los headers de la request ("Could not resolve
        # authentication method..."), antes de que salga ninguna llamada de
        # red. Confirmado corriendo el endpoint real sin API key — sin este
        # except, esa configuración faltante se filtraba como un 500 crudo,
        # justo lo que la Fase 2 pide evitar.
        return GenerationResult(
            answer=None,
            support=None,
            latency_ms=int((time.perf_counter() - start) * 1000),
            error=f"anthropic_client_error: {exc}",
        )

    latency_ms = int((time.perf_counter() - start) * 1000)
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost_usd = _estimate_cost_usd(input_tokens, output_tokens)

    tool_use_block = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_use_block is None:
        return GenerationResult(
            answer=None,
            support=None,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            error="no_tool_use_block",
        )

    try:
        parsed = SubmitAnswerInput.model_validate(tool_use_block.input)
    except ValidationError as exc:
        return GenerationResult(
            answer=None,
            support=None,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            error=f"invalid_tool_output: {exc}",
        )

    citation_valid = all(cid in valid_chunk_ids for cid in parsed.cited_chunk_ids)

    return GenerationResult(
        answer=parsed.answer,
        support=parsed.support,
        cited_chunk_ids=parsed.cited_chunk_ids,
        needs_human=parsed.needs_human,
        needs_human_reason=parsed.needs_human_reason,
        citation_valid=citation_valid,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        error=None,
    )
