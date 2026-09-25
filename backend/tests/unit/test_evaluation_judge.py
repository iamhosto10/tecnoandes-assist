"""Unitarios de `judge_answer` con un cliente de Anthropic simulado a
mano, sin base de datos — mismo patrón que test_generation.py.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import anthropic

from app.evaluation.judge import judge_answer


def _mock_response(tool_input: dict, input_tokens: int = 80, output_tokens: int = 20):
    tool_block = SimpleNamespace(
        type="tool_use", input=tool_input, id="toolu_judge", name="submit_verdict"
    )
    usage = SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)
    return SimpleNamespace(content=[tool_block], usage=usage, stop_reason="tool_use")


def test_verdict_correct_when_answers_match():
    client = MagicMock()
    client.messages.create.return_value = _mock_response(
        {"verdict": "correct", "reason": "Mismo plazo de 30 días."}
    )

    result = judge_answer(
        "¿cuántos días tengo para devolver un producto?",
        "30 días calendario desde la compra.",
        "Tienes 30 días calendario desde la fecha de compra para devolverlo.",
        client,
    )

    assert result.verdict == "correct"
    assert result.input_tokens == 80
    assert result.output_tokens == 20


def test_verdict_incorrect_when_answers_contradict():
    client = MagicMock()
    client.messages.create.return_value = _mock_response(
        {"verdict": "incorrect", "reason": "El plazo real es de 30 días, no de 15."}
    )

    result = judge_answer(
        "¿cuántos días tengo para devolver un producto?",
        "30 días calendario desde la compra.",
        "Tienes 15 días para devolverlo.",
        client,
    )

    assert result.verdict == "incorrect"


def test_anthropic_api_error_is_caught():
    client = MagicMock()
    client.messages.create.side_effect = anthropic.APIConnectionError(
        message="network down", request=MagicMock()
    )

    result = judge_answer("pregunta", "esperada", "real", client)

    assert result.verdict is None
    assert result.reason.startswith("judge_error")


def test_missing_api_key_type_error_is_caught():
    client = MagicMock()
    client.messages.create.side_effect = TypeError("Could not resolve authentication method.")

    result = judge_answer("pregunta", "esperada", "real", client)

    assert result.verdict is None
    assert result.reason.startswith("judge_error")


def test_invalid_verdict_value_is_an_error():
    client = MagicMock()
    client.messages.create.return_value = _mock_response(
        {"verdict": "mas-o-menos", "reason": "no es uno de los valores permitidos"}
    )

    result = judge_answer("pregunta", "esperada", "real", client)

    assert result.verdict is None
    assert "invalid_output" in result.reason
