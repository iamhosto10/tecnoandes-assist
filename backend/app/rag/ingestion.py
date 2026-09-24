"""Ingesta de knowledge_base/*.md hacia la base de datos.

Idempotente por hash: cada chunk guarda un hash sha256 de su propio
contenido, y solo se recalcula el embedding (lo más lento de generar)
para los chunks cuyo hash cambió. Re-correr `make ingest` sin haber
tocado nada no vuelve a llamar al modelo de embeddings para nada.

`ingest_document` también es la función que usa la consola de revisión
para re-ingerir un solo documento después de que un revisor lo edita
(Fase 3) — por eso no asume que viene de un archivo en disco.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import frontmatter
from sqlalchemy.orm import Session

from app.db.models.chunks import Chunk
from app.db.models.documents import Document, DocumentVersion
from app.rag.chunking import chunk_markdown
from app.rag.embeddings import EmbeddingProvider

KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parents[3] / "knowledge_base"

CHUNK_MAX_TOKENS = 300
CHUNK_OVERLAP_TOKENS = 40


@dataclass
class IngestResult:
    slug: str
    action: str  # "created" | "updated" | "unchanged"
    chunks_reused: int
    chunks_recomputed: int


def ingest_document(
    session: Session,
    slug: str,
    title: str,
    category: str,
    content: str,
    embedding_provider: EmbeddingProvider,
    changed_by: str | None = None,
    reason: str | None = None,
    review_item_id: int | None = None,
) -> IngestResult:
    """`changed_by`/`reason`/`review_item_id` solo importan cuando el
    documento YA existe: antes de sobrescribir su contenido, se guarda el
    texto anterior en `document_versions` (ver sección 5 del diseño). La
    ingesta inicial desde Markdown (Fase 1) no los pasa — un `make ingest`
    normal no genera historial de versiones, porque no hay un "revisor"
    detrás de esa carga inicial.
    """
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    document = session.query(Document).filter_by(slug=slug).one_or_none()

    if document is not None and document.content_hash == content_hash:
        return IngestResult(
            slug=slug, action="unchanged", chunks_reused=len(document.chunks), chunks_recomputed=0
        )

    action = "updated" if document is not None else "created"

    if document is not None and changed_by is not None:
        session.add(
            DocumentVersion(
                document_id=document.id,
                content=document.content,  # el texto ANTERIOR, antes de sobrescribirlo
                changed_by=changed_by,
                reason=reason or "",
                review_item_id=review_item_id,
            )
        )

    if document is None:
        document = Document(
            slug=slug, title=title, category=category, content=content, content_hash=content_hash
        )
        session.add(document)
    else:
        document.title = title
        document.category = category
        document.content = content
        document.content_hash = content_hash

    session.flush()  # asegura document.id para las FKs de los chunks nuevos

    new_chunks = chunk_markdown(
        content,
        max_tokens=CHUNK_MAX_TOKENS,
        overlap_tokens=CHUNK_OVERLAP_TOKENS,
        count_tokens=embedding_provider.count_tokens,
    )
    kept_hashes = {r.content_hash for r in new_chunks}

    # `chunk_index` tiene una unique constraint por documento, así que
    # reordenar/borrar chunks existentes puede chocar transitoriamente con
    # una fila vieja que todavía no se borró/movió — Postgres valida esa
    # constraint al ejecutar cada statement, no al final de la transacción.
    # Por eso: primero se borran los chunks que ya no corresponden a ningún
    # contenido actual, y los que se reusan se pasan por un índice temporal
    # negativo (nunca choca con los índices reales, que son >= 0) antes de
    # asignarles su posición final.
    for old_chunk in list(document.chunks):
        if old_chunk.content_hash not in kept_hashes:
            session.delete(old_chunk)
    session.flush()

    existing_by_hash = {c.content_hash: c for c in document.chunks}
    for chunk in existing_by_hash.values():
        chunk.chunk_index = -chunk.id
    session.flush()

    rows: list[Chunk] = []
    pending_embeddings: list[tuple[int, str]] = []  # (índice en `rows`, texto a embeber)
    reused = 0
    recomputed = 0

    for index, result in enumerate(new_chunks):
        existing_chunk = existing_by_hash.get(result.content_hash)

        if existing_chunk is not None:
            existing_chunk.chunk_index = index
            existing_chunk.heading_path = result.heading_path
            rows.append(existing_chunk)
            reused += 1
            continue

        chunk_row = Chunk(
            document_id=document.id,
            chunk_index=index,
            heading_path=result.heading_path,
            content=result.content,
            content_hash=result.content_hash,
            token_count=result.token_count,
            embedding=[0.0] * embedding_provider.dimensions,  # placeholder, se llena abajo
        )
        session.add(chunk_row)
        rows.append(chunk_row)
        # El título del documento va como contexto delante del chunk para que
        # el embedding "sepa" de qué documento viene, sin cambiar el `content`
        # que se le muestra al revisor o se cita en la respuesta.
        embedding_text = f"{title} - {result.heading_path}\n{result.content}"
        pending_embeddings.append((len(rows) - 1, embedding_text))
        recomputed += 1

    if pending_embeddings:
        vectors = embedding_provider.embed_passages([text for _, text in pending_embeddings])
        for (row_index, _), vector in zip(pending_embeddings, vectors, strict=True):
            rows[row_index].embedding = vector

    return IngestResult(
        slug=slug, action=action, chunks_reused=reused, chunks_recomputed=recomputed
    )


def ingest_all(session: Session, embedding_provider: EmbeddingProvider) -> list[IngestResult]:
    results = []
    for path in sorted(KNOWLEDGE_BASE_DIR.glob("*.md")):
        post = frontmatter.load(path)
        result = ingest_document(
            session,
            slug=post.metadata["slug"],
            title=post.metadata["title"],
            category=post.metadata["category"],
            content=post.content.strip(),
            embedding_provider=embedding_provider,
        )
        # Cada documento es su propia transacción: un ingest se puede interrumpir y reanudar.
        session.commit()
        results.append(result)
    return results
