"""Integración: CRUD de documentos (crear, editar con versión, listar,
detalle) contra la Postgres real.
"""

import pytest
from fastapi.testclient import TestClient

from app.db.models.documents import Document
from app.db.session import SessionLocal
from app.main import app

AUTH_HEADERS = {"Authorization": "Bearer change-me-too"}


@pytest.fixture
def http_client():
    return TestClient(app)


@pytest.fixture
def cleanup():
    slugs: list[str] = []
    yield slugs
    if slugs:
        db = SessionLocal()
        try:
            db.query(Document).filter(Document.slug.in_(slugs)).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()


def test_documents_requires_auth(http_client):
    response = http_client.get("/documents")
    assert response.status_code == 401


def test_create_get_and_list_document(http_client, cleanup):
    slug = "_test_productos_drones"
    cleanup.append(slug)

    create_response = http_client.post(
        "/documents",
        headers=AUTH_HEADERS,
        json={
            "slug": slug,
            "title": "Drones (fuera de catálogo)",
            "category": "faq",
            "content": "## Drones\n\nTecnoAndes no vende drones actualmente.",
        },
    )

    assert create_response.status_code == 201
    body = create_response.json()
    assert body["slug"] == slug
    assert body["versions"] == []  # crear no genera historial, no hay "antes"

    get_response = http_client.get(f"/documents/{body['id']}", headers=AUTH_HEADERS)
    assert get_response.status_code == 200

    list_response = http_client.get("/documents", headers=AUTH_HEADERS, params={"q": "Drones"})
    assert list_response.status_code == 200
    assert any(d["slug"] == slug for d in list_response.json()["items"])


def test_duplicate_slug_is_rejected(http_client, cleanup):
    slug = "_test_productos_scooters"
    cleanup.append(slug)
    payload = {
        "slug": slug,
        "title": "Scooters",
        "category": "faq",
        "content": "## Scooters\n\nNo disponibles.",
    }

    first = http_client.post("/documents", headers=AUTH_HEADERS, json=payload)
    assert first.status_code == 201

    second = http_client.post("/documents", headers=AUTH_HEADERS, json=payload)
    assert second.status_code == 409


def test_update_document_creates_a_version_with_the_old_content(http_client, cleanup):
    slug = "_test_politica_prueba"
    cleanup.append(slug)
    original_content = "## Prueba\n\nContenido original."

    created = http_client.post(
        "/documents",
        headers=AUTH_HEADERS,
        json={"slug": slug, "title": "Prueba", "category": "faq", "content": original_content},
    ).json()

    updated = http_client.put(
        f"/documents/{created['id']}",
        headers=AUTH_HEADERS,
        json={
            "content": "## Prueba\n\nContenido corregido con el dato que faltaba.",
            "changed_by": "tester",
            "reason": "Corrección de prueba",
        },
    )

    assert updated.status_code == 200
    body = updated.json()
    assert "corregido" in body["content"]
    assert len(body["versions"]) == 1
    assert body["versions"][0]["content"] == original_content
    assert body["versions"][0]["changed_by"] == "tester"


def test_update_nonexistent_document_is_404(http_client):
    response = http_client.put(
        "/documents/999999999",
        headers=AUTH_HEADERS,
        json={"content": "x", "changed_by": "tester", "reason": "n/a"},
    )
    assert response.status_code == 404
