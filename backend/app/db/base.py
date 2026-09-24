from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa compartida por todos los modelos.

    Los modelos de dominio (documents, chunks, queries, review, evaluation)
    se agregan en las fases que los necesitan; Alembic autogenera las
    migraciones a partir de `Base.metadata`.
    """
