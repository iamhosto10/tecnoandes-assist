"""knowledge base tables: documents, document_versions, chunks

Revision ID: 4c06ff61e735
Revises: 9ee2ff56d85b
Create Date: 2026-09-24 13:54:26.806625

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4c06ff61e735"
down_revision: str | Sequence[str] | None = "9ee2ff56d85b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIMENSIONS = 384  # intfloat/multilingual-e5-small


def _timestamp_column(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    # Configuración de búsqueda de texto propia: primero quita tildes
    # (unaccent) y luego aplica el stemmer en español, para que "telefono"
    # y "teléfono" empaten en la búsqueda de texto completo.
    op.execute("CREATE TEXT SEARCH CONFIGURATION spanish_unaccent (COPY = spanish)")
    op.execute(
        "ALTER TEXT SEARCH CONFIGURATION spanish_unaccent "
        "ALTER MAPPING FOR hword, hword_part, word WITH unaccent, spanish_stem"
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(200), nullable=False, unique=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        _timestamp_column("created_at"),
        _timestamp_column("updated_at"),
    )

    op.create_table(
        "document_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer,
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("changed_by", sa.String(200), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        # FK real a review_items llega en la migración de la Fase 3 (esa
        # tabla todavía no existe en esta fase).
        sa.Column("review_item_id", sa.Integer, nullable=True),
        _timestamp_column("created_at"),
    )

    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer,
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("heading_path", sa.String(500), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=False),
        _timestamp_column("created_at"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_chunks_document_chunk_index"),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])

    # Columna generada: Postgres la recalcula sola a partir de `content`, así
    # nunca puede quedar desincronizada del texto real del chunk.
    op.execute(
        "ALTER TABLE chunks ADD COLUMN content_tsv tsvector "
        "GENERATED ALWAYS AS (to_tsvector('spanish_unaccent', content)) STORED"
    )
    op.execute("CREATE INDEX ix_chunks_content_tsv ON chunks USING GIN (content_tsv)")
    # HNSW: aproximado pero mucho más rápido que un escaneo exacto a medida
    # que crece la tabla; a esta escala (decenas de documentos) la
    # diferencia de recall es despreciable frente a la ganancia de velocidad.
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("ix_chunks_embedding_hnsw", table_name="chunks")
    op.drop_index("ix_chunks_content_tsv", table_name="chunks")
    op.drop_table("chunks")
    op.drop_table("document_versions")
    op.drop_table("documents")
    op.execute("DROP TEXT SEARCH CONFIGURATION IF EXISTS spanish_unaccent")
