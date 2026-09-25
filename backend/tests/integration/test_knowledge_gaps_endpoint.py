"""Integración: GET /review/knowledge-gaps contra la Postgres real y el
modelo de embeddings real (sin LLM de por medio, no hace falta mockear
Anthropic).
"""

import pytest
from fastapi.testclient import TestClient

from app.db.models.queries import Query
from app.db.session import SessionLocal
from app.main import app

AUTH_HEADERS = {"Authorization": "Bearer change-me-too"}

_BASE_QUERY_FIELDS = dict(
    answer="No tengo información suficiente para responder con seguridad en este momento.",
    raw_model_answer=None,
    support="none",
    needs_human=False,
    needs_human_reason=None,
    cited_chunk_ids=[],
    citation_valid=False,
    retrieval_score=0.6,
    retrieval_margin=0.01,
    confidence_score=20.0,
    decision="review",
    rule_applied="no_support",
    generation_error=None,
    latency_ms=100,
    input_tokens=50,
    output_tokens=10,
    cost_usd=0.0001,
)


@pytest.fixture
def http_client():
    return TestClient(app)


@pytest.fixture
def seeded_questions():
    questions = [
        "¿Venden bicicletas?",
        "¿Tienen bicicletas de montaña?",
        "¿Manejan bicicletas eléctricas?",
        "¿Cuál es el horario de atención los domingos?",
    ]
    db = SessionLocal()
    ids: list[int] = []
    try:
        for question in questions:
            row = Query(question=question, **_BASE_QUERY_FIELDS)
            db.add(row)
            db.flush()
            ids.append(row.id)
        db.commit()
        yield questions
    finally:
        db.query(Query).filter(Query.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
        db.close()


def test_knowledge_gaps_requires_auth(http_client):
    response = http_client.get("/review/knowledge-gaps")
    assert response.status_code == 401


def test_bicycle_questions_group_together(http_client, seeded_questions):
    response = http_client.get("/review/knowledge-gaps", headers=AUTH_HEADERS)

    assert response.status_code == 200
    groups = response.json()

    bicycle_group = next(
        (g for g in groups if "bicicleta" in g["representative_question"].lower()), None
    )
    assert bicycle_group is not None
    assert bicycle_group["count"] >= 3
    assert len(bicycle_group["query_ids"]) == bicycle_group["count"]

    # La pregunta del horario no debería mezclarse con el grupo de bicicletas.
    assert not any(
        "horario" in q.lower() for q in bicycle_group["example_questions"]
    )
