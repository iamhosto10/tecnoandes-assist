"""Importar todos los módulos de modelos aquí para que se registren en
Base.metadata antes de que algo (Alembic autogenerate, la primera query)
necesite el grafo de mappers completo.
"""

from app.db.models.chunks import Chunk
from app.db.models.documents import Document, DocumentVersion
from app.db.models.queries import Query, QueryChunk
from app.db.models.review import ReviewAction, ReviewItem

__all__ = [
    "Chunk",
    "Document",
    "DocumentVersion",
    "Query",
    "QueryChunk",
    "ReviewAction",
    "ReviewItem",
]
