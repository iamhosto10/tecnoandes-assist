"""evaluation cases, runs and results tables

Revision ID: 28d5b738e89e
Revises: 196ae1f67435
Create Date: 2026-09-25 14:08:12.152062

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "28d5b738e89e"
down_revision: str | Sequence[str] | None = "196ae1f67435"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# NOTA: `alembic revision --autogenerate` también detectó drift preexistente
# entre los modelos y la base (tipos de timestamp sin timezone, índices y
# constraints que ya no coinciden) que no tiene nada que ver con esta
# migración — se descartó del autogenerado y esta migración solo toca las
# tres tablas nuevas de evaluación, igual que se hizo a mano en
# 196ae1f67435 (review_items/review_actions).


def _timestamp_column(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("config_snapshot", postgresql.JSONB, nullable=False),
        sa.Column("metrics", postgresql.JSONB, nullable=False),
        _timestamp_column("created_at"),
    )

    op.create_table(
        "evaluation_cases",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("expected_answer", sa.Text, nullable=True),
        sa.Column("expected_doc_slugs", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("should_escalate", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("origin", sa.String(20), nullable=False, server_default="seed"),
        sa.Column(
            "source_review_item_id",
            sa.Integer,
            sa.ForeignKey("review_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        _timestamp_column("created_at"),
    )

    op.create_table(
        "evaluation_results",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "run_id", sa.Integer, sa.ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "case_id", sa.Integer, sa.ForeignKey("evaluation_cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actual_answer", sa.Text, nullable=False),
        sa.Column("actual_doc_slugs", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("recall_at_k", sa.Float, nullable=True),
        sa.Column("judge_verdict", sa.String(20), nullable=True),
        sa.Column("judge_reason", sa.Text, nullable=True),
        sa.Column("routing_correct", sa.Boolean, nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("confidence_score", sa.Float, nullable=False),
        sa.Column("latency_ms", sa.Integer, nullable=False),
        sa.Column("cost_usd", sa.Float, nullable=False),
        _timestamp_column("created_at"),
    )
    op.create_index("ix_evaluation_results_run_id", "evaluation_results", ["run_id"])
    op.create_index("ix_evaluation_results_case_id", "evaluation_results", ["case_id"])


def downgrade() -> None:
    op.drop_index("ix_evaluation_results_case_id", table_name="evaluation_results")
    op.drop_index("ix_evaluation_results_run_id", table_name="evaluation_results")
    op.drop_table("evaluation_results")
    op.drop_table("evaluation_cases")
    op.drop_table("evaluation_runs")
