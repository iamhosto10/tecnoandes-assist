"""Juez LLM: compara la respuesta real del pipeline contra la esperada de
`eval/seed.jsonl`. Mismo patrón que `app/rag/generation.py` — tool use
forzado con `strict: true`, para no depender de que el modelo devuelva
JSON bien formado en texto libre.

El juez evalúa si la respuesta dice lo mismo que la esperada, NO le pide
al modelo su propia confianza ni una nota subjetiva de calidad — eso es
justo lo que el diseño original pide evitar ("nunca le pidas al LLM que
se autoevalúe su propia confianza"). Acá el LLM compara dos textos contra
una pregunta puntual, un juicio de hechos, no una introspección.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import anthropic
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings

JudgeVerdict = Literal["correct", "partial", "incorrect"]

_JUDGE_TOOL = {
    "name": "submit_verdict",
    "description": "Entrega el veredicto sobre si la respuesta real coincide con la esperada.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["correct", "partial", "incorrect"],
                "description": (
                    "correct: dice lo mismo que la esperada (mismos datos, aunque cambien "
                    "las palabras). partial: acierta en parte pero falta o cambia un dato "
                    "concreto (precio, plazo, sede). incorrect: contradice la esperada o no "
                    "responde la pregunta."
                ),
            },
            "reason": {
                "type": "string",
                "description": "Una frase breve explicando el veredicto.",
            },
        },
        "required": ["verdict", "reason"],
        "additionalProperties": False,
    },
}

_JUDGE_SYSTEM_PROMPT = """Eres un juez que compara dos respuestas a la misma pregunta de un \
cliente de TecnoAndes: una respuesta ESPERADA (la correcta, de referencia) y una respuesta \
REAL (la que dio el sistema que se está evaluando).

Juzga solo si la respuesta real coincide en los HECHOS con la esperada (precios, plazos, \
sedes, políticas) — ignora diferencias de redacción, longitud u orden. Responde siempre \
llamando a la herramienta submit_verdict."""


class _VerdictOutput(BaseModel):
    verdict: JudgeVerdict
    reason: str


@dataclass
class JudgeResult:
    verdict: JudgeVerdict | None
    reason: str
    input_tokens: int = 0
    output_tokens: int = 0


def judge_answer(
    question: str,
    expected_answer: str,
    actual_answer: str,
    client: anthropic.Anthropic,
) -> JudgeResult:
    settings = get_settings()
    user_message = (
        f"Pregunta del cliente: {question}\n\n"
        f"Respuesta esperada: {expected_answer}\n\n"
        f"Respuesta real: {actual_answer}"
    )

    try:
        response = client.messages.create(
            model=settings.anthropic_judge_model,
            max_tokens=512,
            system=_JUDGE_SYSTEM_PROMPT,
            tools=[_JUDGE_TOOL],
            tool_choice={"type": "tool", "name": "submit_verdict"},
            messages=[{"role": "user", "content": user_message}],
        )
    except (anthropic.APIError, TypeError) as exc:
        # Mismo manejo que generate_answer: el SDK puede lanzar un TypeError
        # plano sin ninguna credencial configurada, no solo anthropic.APIError.
        return JudgeResult(verdict=None, reason=f"judge_error: {exc}")

    tool_use_block = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_use_block is None:
        return JudgeResult(verdict=None, reason="judge_error: no_tool_use_block")

    try:
        parsed = _VerdictOutput.model_validate(tool_use_block.input)
    except ValidationError as exc:
        return JudgeResult(verdict=None, reason=f"judge_error: invalid_output: {exc}")

    return JudgeResult(
        verdict=parsed.verdict,
        reason=parsed.reason,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
