"""Consulta y filtrado de la cola de revisión. Separado del router
(app/api/review.py) para que la lógica de filtros/paginación se pueda
testear sin pasar por HTTP.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.queries import Query
from app.db.models.review import ReviewItem


@dataclass
class ReviewItemListResult:
    items: list[ReviewItem]
    total: int


def list_review_items(
    session: Session,
    status: str | None = None,
    reason: str | None = None,
    confidence_min: float | None = None,
    confidence_max: float | None = None,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    limit: int = 20,
    offset: int = 0,
) -> ReviewItemListResult:
    stmt = select(ReviewItem).join(Query, ReviewItem.query_id == Query.id)

    if status is not None:
        stmt = stmt.where(ReviewItem.status == status)
    if reason is not None:
        stmt = stmt.where(ReviewItem.reason == reason)
    if confidence_min is not None:
        stmt = stmt.where(Query.confidence_score >= confidence_min)
    if confidence_max is not None:
        stmt = stmt.where(Query.confidence_score <= confidence_max)
    if date_from is not None:
        stmt = stmt.where(ReviewItem.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(ReviewItem.created_at < date_to + dt.timedelta(days=1))

    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    stmt = stmt.order_by(ReviewItem.created_at.desc()).limit(limit).offset(offset)
    items = list(session.scalars(stmt).all())

    return ReviewItemListResult(items=items, total=total)
