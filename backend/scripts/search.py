#!/usr/bin/env python
"""CLI: solo retrieval, sin LLM — para depurar la búsqueda por separado.

La mayoría de los errores de un RAG vienen de la búsqueda, no de la
generación; este script deja ver exactamente qué trae el retrieval
híbrido y con qué puntajes, antes de que un LLM entre a la ecuación.

Uso: make search q="pregunta"  (o `uv run python scripts/search.py "pregunta"`)
"""

import sys

from app.db.session import session_scope
from app.rag.embeddings import get_embedding_provider
from app.rag.retrieval import hybrid_search


def main() -> None:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print('Uso: make search q="tu pregunta"')
        raise SystemExit(1)

    query = sys.argv[1]
    embedding_provider = get_embedding_provider()

    with session_scope() as session:
        results = hybrid_search(session, query, embedding_provider)

    if not results:
        print("Sin resultados.")
        return

    for rank, r in enumerate(results, start=1):
        print(f"\n#{rank} [{r.document_slug}] {r.heading_path or '(sin encabezado)'}")
        print(
            f"    rrf={r.rrf_score:.4f}  "
            f"vector={r.vector_score:.4f} (rank {r.vector_rank})  "
            f"fulltext={r.fulltext_score:.4f} (rank {r.fulltext_rank})"
        )
        preview = r.content[:200].replace("\n", " ")
        suffix = "..." if len(r.content) > 200 else ""
        print(f"    {preview}{suffix}")


if __name__ == "__main__":
    main()
