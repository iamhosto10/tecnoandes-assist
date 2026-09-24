"""review_items and review_actions tables

Revision ID: 196ae1f67435
Revises: c58f3e4d031c
Create Date: 2026-09-24 15:02:10.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "196ae1f67435"
down_revision: str | Sequence[str] | None = "c58f3e4d031c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamp_column(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "review_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "query_id", sa.Integer, sa.ForeignKey("queries.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reason", sa.String(50), nullable=False),
        _timestamp_column("created_at"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(200), nullable=True),
    )
    op.create_index("ix_review_items_query_id", "review_items", ["query_id"])
    op.create_index("ix_review_items_status", "review_items", ["status"])

    op.create_table(
        "review_actions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "review_item_id",
            sa.Integer,
            sa.ForeignKey("review_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action_type", sa.String(40), nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("actor", sa.String(200), nullable=False),
        sa.Column(
            "document_id",
            sa.Integer,
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        _timestamp_column("created_at"),
    )
    op.create_index("ix_review_actions_review_item_id", "review_actions", ["review_item_id"])

    # FK diferida desde la Fase 1: `document_versions.review_item_id` ya
    # existía como entero suelto porque `review_items` todavía no existía.
    op.create_foreign_key(
        "fk_document_versions_review_item",
        "document_versions",
        "review_items",
        ["review_item_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_document_versions_review_item", "document_versions", type_="foreignkey"
    )
    op.drop_table("review_actions")
    op.drop_index("ix_review_items_status", table_name="review_items")
    op.drop_index("ix_review_items_query_id", table_name="review_items")
    op.drop_table("review_items")
