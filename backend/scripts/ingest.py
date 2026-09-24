#!/usr/bin/env python
"""CLI: procesa knowledge_base/*.md -> chunks + embeddings en la DB.

Uso: make ingest  (o `uv run python scripts/ingest.py` desde backend/)
"""

from app.db.session import session_scope
from app.rag.embeddings import get_embedding_provider
from app.rag.ingestion import ingest_all


def main() -> None:
    embedding_provider = get_embedding_provider()
    with session_scope() as session:
        results = ingest_all(session, embedding_provider)

    for r in results:
        print(
            f"[{r.action:9s}] {r.slug:40s} "
            f"chunks: {r.chunks_reused} reusados, {r.chunks_recomputed} recalculados"
        )

    print(f"\n{len(results)} documentos procesados.")


if __name__ == "__main__":
    main()
