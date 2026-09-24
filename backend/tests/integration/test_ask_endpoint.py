"""Integración: POST /ask con el cliente de Anthropic simulado (mock).

Retrieval y la base de datos son reales (Postgres real, embeddings E5
reales) — lo único que se simula es la llamada al LLM, tal como pide el
diseño ("tests de integración para la API, con el cliente de Anthropic
simulado"). Necesita `make up` corriendo y `make ingest` ya ejecutado.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.db.models.queries import Query
from app.db.session import SessionLocal
from app.main import app
from app.rag.generation import get_anthropic_client


def _mock_response(tool_input: dict, input_tokens: int = 120, output_tokens: int = 40):
    tool_block = SimpleNamespace(
        type="tool_use", input=tool_input, id="toolu_test", name="submit_answer"
    )
    usage = SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)
    return SimpleNamespace(content=[tool_block], usage=usage, stop_reason="tool_use")


@pytest.fixture
def mock_anthropic_client():
    client = MagicMock()
    app.dependency_overrides[get_anthropic_client] = lambda: client
    yield client
    app.dependency_overrides.pop(get_anthropic_client, None)


@pytest.fixture
def http_client():
    return TestClient(app)


@pytest.fixture
def created_query_ids():
    ids: list[int] = []
    yield ids
    if ids:
        db = SessionLocal()
        db.query(Query).filter(Query.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
        db.close()


def test_direct_answer_when_model_is_fully_confident(
    http_client, mock_anthropic_client, created_query_ids
):
    mock_anthropic_client.messages.create.return_value = _mock_response(
        {
            "answer": "El iPhone 13 cuesta $3.199.000 COP.",
            "support": "full",
            "cited_chunk_ids": [],
            "needs_human": False,
            "needs_human_reason": None,
        }
    )

    response = http_client.post("/ask", json={"question": "cuanto cuesta el iPhone 13"})

    assert response.status_code == 200
    body = response.json()
    created_query_ids.append(body["query_id"])
    assert body["decision"] == "direct"
    assert body["answer"] == "El iPhone 13 cuesta $3.199.000 COP."


def test_needs_human_escalates(http_client, mock_anthropic_client, created_query_ids):
    mock_anthropic_client.messages.create.return_value = _mock_response(
        {
            "answer": "Lamento el inconveniente, un asesor te contactará pronto.",
            "support": "full",
            "cited_chunk_ids": [],
            "needs_human": True,
            "needs_human_reason": "Reclamo por cobro duplicado",
        }
    )

    response = http_client.post("/ask", json={"question": "me cobraron dos veces"})

    body = response.json()
    created_query_ids.append(body["query_id"])
    assert body["decision"] == "escalate"
    assert body["answer"] == "Lamento el inconveniente, un asesor te contactará pronto."


def test_support_none_goes_to_review_with_fallback_answer(
    http_client, mock_anthropic_client, created_query_ids
):
    mock_anthropic_client.messages.create.return_value = _mock_response(
        {
            "answer": "No encontré información sobre bicicletas.",
            "support": "none",
            "cited_chunk_ids": [],
            "needs_human": False,
            "needs_human_reason": None,
        }
    )

    response = http_client.post("/ask", json={"question": "venden bicicletas?"})

    body = response.json()
    created_query_ids.append(body["query_id"])
    assert body["decision"] == "review"
    # La respuesta cruda del modelo no se muestra directo en "review".
    assert body["answer"] != "No encontré información sobre bicicletas."
    assert body["confidence"]["support"] == "none"


def test_support_partial_warns_and_still_shows_the_answer(
    http_client, mock_anthropic_client, created_query_ids
):
    mock_anthropic_client.messages.create.return_value = _mock_response(
        {
            "answer": "Tenemos el Samsung Galaxy S23, pero no tengo el color disponible.",
            "support": "partial",
            "cited_chunk_ids": [],
            "needs_human": False,
            "needs_human_reason": None,
        }
    )

    response = http_client.post("/ask", json={"question": "el Samsung viene en azul?"})

    body = response.json()
    created_query_ids.append(body["query_id"])
    assert body["decision"] == "warn"
    assert body["answer"] == "Tenemos el Samsung Galaxy S23, pero no tengo el color disponible."


def test_invalid_citation_goes_to_review(http_client, mock_anthropic_client, created_query_ids):
    mock_anthropic_client.messages.create.return_value = _mock_response(
        {
            "answer": "Respuesta con una cita inventada.",
            "support": "full",
            "cited_chunk_ids": [999999999],  # no existe en el contexto recuperado
            "needs_human": False,
            "needs_human_reason": None,
        }
    )

    response = http_client.post("/ask", json={"question": "cuales son las sedes"})

    body = response.json()
    created_query_ids.append(body["query_id"])
    assert body["decision"] == "review"
    assert body["confidence"]["citation_valid"] is False


def test_invalid_tool_output_goes_to_review(http_client, mock_anthropic_client, created_query_ids):
    # "support" no es uno de los valores permitidos -> falla la validación Pydantic.
    mock_anthropic_client.messages.create.return_value = _mock_response(
        {
            "answer": "...",
            "support": "algo-invalido",
            "cited_chunk_ids": [],
            "needs_human": False,
            "needs_human_reason": None,
        }
    )

    response = http_client.post("/ask", json={"question": "hola"})

    body = response.json()
    created_query_ids.append(body["query_id"])
    assert body["decision"] == "review"


def test_query_and_retrieved_chunks_are_persisted(
    http_client, mock_anthropic_client, created_query_ids
):
    mock_anthropic_client.messages.create.return_value = _mock_response(
        {
            "answer": "Bogotá, Medellín, Barranquilla y Valledupar.",
            "support": "full",
            "cited_chunk_ids": [],
            "needs_human": False,
            "needs_human_reason": None,
        }
    )

    response = http_client.post("/ask", json={"question": "en que ciudades tienen sede"})
    body = response.json()
    created_query_ids.append(body["query_id"])

    db = SessionLocal()
    try:
        stored = db.get(Query, body["query_id"])
        assert stored is not None
        assert stored.question == "en que ciudades tienen sede"
        assert len(stored.retrieved_chunks) == len(body["sources"])
    finally:
        db.close()
