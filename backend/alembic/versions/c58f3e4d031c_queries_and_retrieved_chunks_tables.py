"""queries and retrieved_chunks tables

Revision ID: c58f3e4d031c
Revises: 4c06ff61e735
Create Date: 2026-09-24 14:15:50.379950

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c58f3e4d031c"
down_revision: str | Sequence[str] | None = "4c06ff61e735"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamp_column(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "queries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("answer", sa.Text, nullable=False),
        sa.Column("raw_model_answer", sa.Text, nullable=True),
        sa.Column("support", sa.String(10), nullable=True),
        sa.Column("needs_human", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("needs_human_reason", sa.Text, nullable=True),
        sa.Column(
            "cited_chunk_ids", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column("citation_valid", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("retrieval_score", sa.Float, nullable=False),
        sa.Column("retrieval_margin", sa.Float, nullable=False),
        sa.Column("confidence_score", sa.Float, nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("rule_applied", sa.String(50), nullable=False),
        sa.Column("generation_error", sa.Text, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=False),
        sa.Column("output_tokens", sa.Integer, nullable=False),
        sa.Column("cost_usd", sa.Float, nullable=False),
        _timestamp_column("created_at"),
    )
    op.create_index("ix_queries_created_at", "queries", ["created_at"])
    op.create_index("ix_queries_decision", "queries", ["decision"])

    op.create_table(
        "retrieved_chunks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "query_id", sa.Integer, sa.ForeignKey("queries.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "chunk_id", sa.Integer, sa.ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("rank", sa.Integer, nullable=False),
        sa.Column("vector_score", sa.Float, nullable=False),
        sa.Column("fulltext_score", sa.Float, nullable=False),
        sa.Column("rrf_score", sa.Float, nullable=False),
    )
    op.create_index("ix_retrieved_chunks_query_id", "retrieved_chunks", ["query_id"])


def downgrade() -> None:
    op.drop_table("retrieved_chunks")
    op.drop_index("ix_queries_decision", table_name="queries")
    op.drop_index("ix_queries_created_at", table_name="queries")
    op.drop_table("queries")
