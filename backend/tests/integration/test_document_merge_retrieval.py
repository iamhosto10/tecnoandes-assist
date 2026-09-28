"""Integración: `hybrid_search` trae un documento completo cuando domina
claramente el top de candidatos (pregunta amplia, "¿qué celulares
tienen?"), pero NO lo hace para una pregunta puntual sobre un producto
específico — aunque productos de la misma categoría también aparezcan
entre los candidatos. Ver el comentario de DOCUMENT_MERGE_* en
app/rag/retrieval.py para el porqué del umbral.

Necesita `make up` + `make ingest` ya corridos contra el catálogo real
(productos-celulares tiene más de 10 productos).
"""

from app.db.session import SessionLocal
from app.rag.embeddings import get_embedding_provider
from app.rag.retrieval import hybrid_search


def test_broad_category_question_merges_the_full_document():
    db = SessionLocal()
    try:
        results = hybrid_search(db, "que celulares tienes disponibles", get_embedding_provider())
        celular_chunks = [r for r in results if r.document_slug == "productos-celulares"]

        # El catálogo real tiene 12 celulares + la intro; si el merge
        # funcionó, deberían estar TODOS, no solo un puñado.
        assert len(celular_chunks) >= 10
        headings = {c.heading_path for c in celular_chunks}
        assert any("iPhone 13" in h for h in headings)
        assert any("Xiaomi" in h for h in headings)
    finally:
        db.close()


def test_specific_product_question_does_not_merge():
    db = SessionLocal()
    try:
        results = hybrid_search(db, "cuanto cuesta el iPhone 13", get_embedding_provider())

        # Sin el merge, top_k=5 sigue mandando — una pregunta puntual no
        # debe arrastrar el catálogo completo de celulares.
        assert len(results) == 5
        celular_chunks = [r for r in results if r.document_slug == "productos-celulares"]
        assert len(celular_chunks) < 10
    finally:
        db.close()
