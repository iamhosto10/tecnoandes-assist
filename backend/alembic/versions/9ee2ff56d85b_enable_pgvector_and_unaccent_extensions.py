"""enable pgvector and unaccent extensions

Revision ID: 9ee2ff56d85b
Revises: 
Create Date: 2026-09-24 12:28:11.917341

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9ee2ff56d85b'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # pgvector: tipo `vector` y operadores de distancia para los embeddings.
    # unaccent: usado en el índice de texto completo en español para que
    # "telefono" y "teléfono" empaten en la búsqueda.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS unaccent")
    op.execute("DROP EXTENSION IF EXISTS vector")
