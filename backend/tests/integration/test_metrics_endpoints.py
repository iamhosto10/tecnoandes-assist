"""Integración: GET /metrics/summary y /metrics/evaluation-runs contra la
Postgres real. No fija valores exactos de conteos (la base ya tiene datos
de otros tests/uso manual) — solo la forma de la respuesta y que el total
de queries y el de corridas de evaluación sean coherentes con lo que hay.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

AUTH_HEADERS = {"Authorization": "Bearer change-me-too"}


@pytest.fixture
def http_client():
    return TestClient(app)


def test_summary_requires_auth(http_client):
    response = http_client.get("/metrics/summary")
    assert response.status_code == 401


def test_summary_shape(http_client):
    response = http_client.get("/metrics/summary", headers=AUTH_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "total_queries",
        "decision_counts",
        "avg_confidence_score",
        "avg_latency_ms",
        "total_cost_usd",
        "pending_review_count",
        "document_count",
    }
    assert isinstance(body["decision_counts"], dict)
    assert body["total_queries"] >= 0
    assert body["document_count"] >= 0


def test_evaluation_runs_requires_auth(http_client):
    response = http_client.get("/metrics/evaluation-runs")
    assert response.status_code == 401


def test_evaluation_runs_shape(http_client):
    response = http_client.get("/metrics/evaluation-runs", headers=AUTH_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert "runs" in body
    assert isinstance(body["runs"], list)
    for run in body["runs"]:
        assert set(run) == {"id", "created_at", "metrics", "config_snapshot"}
