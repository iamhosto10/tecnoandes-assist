"""Integración: cola de revisión, detalle, acciones y re-prueba, contra
la Postgres real. El cliente de Anthropic se simula, igual que en
test_ask_endpoint.py — el token de la consola es el valor por defecto de
Settings (coincide con .env.example).
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.db.models.documents import Document
from app.db.models.queries import Query
from app.db.models.review import ReviewItem
from app.db.session import SessionLocal
from app.main import app
from app.rag.generation import get_anthropic_client

AUTH_HEADERS = {"Authorization": "Bearer change-me-too"}


def _mock_response(tool_input: dict, input_tokens: int = 100, output_tokens: int = 30):
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
def cleanup():
    query_ids: list[int] = []
    document_slugs: list[str] = []
    yield {"query_ids": query_ids, "document_slugs": document_slugs}
    db = SessionLocal()
    try:
        if query_ids:
            db.query(Query).filter(Query.id.in_(query_ids)).delete(synchronize_session=False)
        if document_slugs:
            db.query(Document).filter(Document.slug.in_(document_slugs)).delete(
                synchronize_session=False
            )
        db.commit()
    finally:
        db.close()


def _create_review_item(http_client, mock_anthropic_client, cleanup, question: str) -> int:
    """Crea un caso de revisión real vía /ask (support=none -> decision=review)."""
    mock_anthropic_client.messages.create.return_value = _mock_response(
        {
            "answer": "No tengo esa información.",
            "support": "none",
            "cited_chunk_ids": [],
            "needs_human": False,
            "needs_human_reason": None,
        }
    )
    response = http_client.post("/ask", json={"question": question})
    body = response.json()
    cleanup["query_ids"].append(body["query_id"])

    db = SessionLocal()
    try:
        item = db.query(ReviewItem).filter_by(query_id=body["query_id"]).one()
        return item.id
    finally:
        db.close()


def test_review_items_requires_auth(http_client):
    response = http_client.get("/review/items")
    assert response.status_code == 401


def test_review_items_lists_pending_case(http_client, mock_anthropic_client, cleanup):
    item_id = _create_review_item(http_client, mock_anthropic_client, cleanup, "venden drones?")

    response = http_client.get("/review/items", headers=AUTH_HEADERS, params={"status": "pending"})

    assert response.status_code == 200
    body = response.json()
    assert any(i["id"] == item_id for i in body["items"])


def test_review_item_detail_includes_sources_and_confidence(
    http_client, mock_anthropic_client, cleanup
):
    item_id = _create_review_item(
        http_client, mock_anthropic_client, cleanup, "venden bicicletas electricas?"
    )

    response = http_client.get(f"/review/items/{item_id}", headers=AUTH_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["reason"] == "no_support"
    assert "sources" in body and isinstance(body["sources"], list)
    assert body["confidence"]["support"] == "none"


def test_approve_action_resolves_the_item(http_client, mock_anthropic_client, cleanup):
    item_id = _create_review_item(http_client, mock_anthropic_client, cleanup, "venden patinetas?")

    response = http_client.post(
        f"/review/items/{item_id}/actions",
        headers=AUTH_HEADERS,
        json={"action_type": "approve", "actor": "tester"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["resolved_at"] is not None
    assert body["actions"][-1]["action_type"] == "approve"


def test_correct_action_updates_the_answer(http_client, mock_anthropic_client, cleanup):
    item_id = _create_review_item(
        http_client, mock_anthropic_client, cleanup, "venden monopatines?"
    )

    response = http_client.post(
        f"/review/items/{item_id}/actions",
        headers=AUTH_HEADERS,
        json={
            "action_type": "correct",
            "corrected_answer": "No vendemos monopatines por ahora.",
            "actor": "tester",
        },
    )

    body = response.json()
    assert body["status"] == "corrected"
    assert body["answer"] == "No vendemos monopatines por ahora."


def test_correct_without_answer_is_rejected(http_client, mock_anthropic_client, cleanup):
    item_id = _create_review_item(http_client, mock_anthropic_client, cleanup, "venden cascos?")

    response = http_client.post(
        f"/review/items/{item_id}/actions",
        headers=AUTH_HEADERS,
        json={"action_type": "correct"},
    )

    assert response.status_code == 400


def test_escalate_without_note_is_rejected(http_client, mock_anthropic_client, cleanup):
    item_id = _create_review_item(http_client, mock_anthropic_client, cleanup, "venden scooters?")

    response = http_client.post(
        f"/review/items/{item_id}/actions",
        headers=AUTH_HEADERS,
        json={"action_type": "escalate"},
    )

    assert response.status_code == 400


def test_correct_and_create_document_creates_and_ingests(
    http_client, mock_anthropic_client, cleanup
):
    item_id = _create_review_item(
        http_client, mock_anthropic_client, cleanup, "venden bicicletas de montaña?"
    )
    slug = "_test_productos_bicicletas"
    cleanup["document_slugs"].append(slug)

    response = http_client.post(
        f"/review/items/{item_id}/actions",
        headers=AUTH_HEADERS,
        json={
            "action_type": "correct_and_create_document",
            "corrected_answer": "No vendemos bicicletas.",
            "actor": "tester",
            "new_document": {
                "slug": slug,
                "title": "Bicicletas (fuera de catálogo)",
                "category": "faq",
                "content": "## Bicicletas\n\nTecnoAndes no vende bicicletas.",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "corrected"
    created_document_id = body["actions"][-1]["document_id"]
    assert created_document_id is not None

    doc_response = http_client.get(f"/documents/{created_document_id}", headers=AUTH_HEADERS)
    assert doc_response.status_code == 200
    assert doc_response.json()["slug"] == slug


def test_retest_does_not_create_a_new_query(http_client, mock_anthropic_client, cleanup):
    item_id = _create_review_item(
        http_client, mock_anthropic_client, cleanup, "cual es el horario de la sede de Cali?"
    )

    db = SessionLocal()
    try:
        count_before = db.query(Query).count()
    finally:
        db.close()

    mock_anthropic_client.messages.create.return_value = _mock_response(
        {
            "answer": "No tenemos sede en Cali.",
            "support": "full",
            "cited_chunk_ids": [],
            "needs_human": False,
            "needs_human_reason": None,
        }
    )

    response = http_client.post(f"/review/items/{item_id}/retest", headers=AUTH_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["before"]["decision"] == "review"
    # No fijamos un umbral exacto de confianza (eso depende de la similitud
    # real del embedding, ruidosa por diseño); lo que importa es que
    # support="full" ya no cae en "review" y la respuesta cambió.
    assert body["after"]["decision"] in ("warn", "direct")
    assert body["after"]["answer"] == "No tenemos sede en Cali."

    db = SessionLocal()
    try:
        count_after = db.query(Query).count()
    finally:
        db.close()
    assert count_after == count_before
