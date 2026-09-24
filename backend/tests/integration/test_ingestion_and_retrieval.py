"""Integración: ingest_document + hybrid_search contra una Postgres real.

A diferencia de los tests unitarios, estos SÍ necesitan la base de datos
levantada (`make up`) y el modelo de embeddings ya descargado — por eso
viven aparte, en tests/integration/. No usan ANTHROPIC_API_KEY ni llaman
a ningún LLM, así que no están marcados como `live`.
"""

import pytest

from app.db.models.documents import Document
from app.db.session import SessionLocal
from app.rag.embeddings import get_embedding_provider
from app.rag.ingestion import ingest_document
from app.rag.retrieval import hybrid_search

TEST_SLUG = "_test_integration_doc"


@pytest.fixture
def session():
    db = SessionLocal()
    try:
        yield db
    finally:
        # Limpieza: el documento de prueba nunca debe quedar en la DB real.
        db.query(Document).filter_by(slug=TEST_SLUG).delete()
        db.commit()
        db.close()


@pytest.fixture(scope="module")
def embedding_provider():
    return get_embedding_provider()


def test_ingest_then_search_finds_the_document(session, embedding_provider):
    content = "## Envíos a Marte\n\nTecnoAndes todavía no envía productos al planeta Marte."

    result = ingest_document(
        session,
        slug=TEST_SLUG,
        title="Documento de prueba",
        category="test",
        content=content,
        embedding_provider=embedding_provider,
    )
    session.commit()

    assert result.action == "created"
    assert result.chunks_recomputed == 1

    hits = hybrid_search(session, "¿envían productos a Marte?", embedding_provider, top_k=5)

    assert any(h.document_slug == TEST_SLUG for h in hits)


def test_reingesting_unchanged_content_recomputes_nothing(session, embedding_provider):
    content = "## Sección\n\nContenido sin cambios entre las dos ingestas."

    first = ingest_document(
        session,
        slug=TEST_SLUG,
        title="Doc",
        category="test",
        content=content,
        embedding_provider=embedding_provider,
    )
    session.commit()

    second = ingest_document(
        session,
        slug=TEST_SLUG,
        title="Doc",
        category="test",
        content=content,
        embedding_provider=embedding_provider,
    )
    session.commit()

    assert first.action == "created"
    assert second.action == "unchanged"
    assert second.chunks_recomputed == 0
