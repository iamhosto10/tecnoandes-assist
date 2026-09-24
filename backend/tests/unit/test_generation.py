"""Unitarios de `generate_answer` con un cliente de Anthropic simulado a
mano (MagicMock), sin FastAPI ni base de datos — solo la lógica de
parseo/validación/manejo de errores.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import anthropic

from app.rag.generation import generate_answer
from app.rag.retrieval import RetrievedChunk

CHUNK = RetrievedChunk(
    chunk_id=1,
    document_id=1,
    document_title="Política de devoluciones",
    document_slug="politica-devoluciones",
    heading_path="Plazo",
    content="30 días calendario con factura.",
    vector_score=0.85,
    fulltext_score=0.1,
    rrf_score=0.02,
    vector_rank=1,
    fulltext_rank=None,
)


def _mock_response(tool_input: dict, input_tokens: int = 100, output_tokens: int = 30):
    tool_block = SimpleNamespace(
        type="tool_use", input=tool_input, id="toolu_1", name="submit_answer"
    )
    usage = SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)
    return SimpleNamespace(content=[tool_block], usage=usage, stop_reason="tool_use")


def test_happy_path_parses_and_validates_citations():
    client = MagicMock()
    client.messages.create.return_value = _mock_response(
        {
            "answer": "Puedes devolverlo dentro de 30 días.",
            "support": "full",
            "cited_chunk_ids": [1],
            "needs_human": False,
            "needs_human_reason": None,
        }
    )

    result = generate_answer("puedo devolverlo?", [CHUNK], client)

    assert result.error is None
    assert result.answer == "Puedes devolverlo dentro de 30 días."
    assert result.support == "full"
    assert result.citation_valid is True
    assert result.input_tokens == 100
    assert result.output_tokens == 30
    assert result.cost_usd > 0


def test_citation_outside_context_is_flagged_invalid():
    client = MagicMock()
    client.messages.create.return_value = _mock_response(
        {
            "answer": "...",
            "support": "full",
            "cited_chunk_ids": [999],  # no está entre los chunks pasados
            "needs_human": False,
            "needs_human_reason": None,
        }
    )

    result = generate_answer("pregunta", [CHUNK], client)

    assert result.error is None
    assert result.citation_valid is False


def test_no_tool_use_block_is_an_error():
    client = MagicMock()
    text_block = SimpleNamespace(type="text", text="respuesta en texto plano")
    client.messages.create.return_value = SimpleNamespace(
        content=[text_block],
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        stop_reason="end_turn",
    )

    result = generate_answer("pregunta", [CHUNK], client)

    assert result.error == "no_tool_use_block"
    assert result.answer is None


def test_invalid_tool_input_is_an_error():
    client = MagicMock()
    client.messages.create.return_value = _mock_response(
        {
            "answer": "...",
            "support": "un-valor-invalido",  # no es full/partial/none
            "cited_chunk_ids": [],
            "needs_human": False,
            "needs_human_reason": None,
        }
    )

    result = generate_answer("pregunta", [CHUNK], client)

    assert result.error is not None
    assert result.error.startswith("invalid_tool_output")


def test_anthropic_api_error_is_caught():
    client = MagicMock()
    client.messages.create.side_effect = anthropic.APIConnectionError(
        message="network down", request=MagicMock()
    )

    result = generate_answer("pregunta", [CHUNK], client)

    assert result.error is not None
    assert result.error.startswith("anthropic_api_error")
    assert result.answer is None


def test_missing_api_key_type_error_is_caught_not_leaked_as_500():
    # El SDK levanta un TypeError plano (no anthropic.APIError) cuando no
    # hay ninguna credencial configurada — comportamiento real, confirmado
    # corriendo el endpoint sin ANTHROPIC_API_KEY. Sin este manejo, esto se
    # filtraba como un error técnico crudo al cliente.
    client = MagicMock()
    client.messages.create.side_effect = TypeError(
        "Could not resolve authentication method. Expected one of api_key, "
        "auth_token, or credentials to be set."
    )

    result = generate_answer("pregunta", [CHUNK], client)

    assert result.error is not None
    assert result.error.startswith("anthropic_client_error")
    assert result.answer is None
