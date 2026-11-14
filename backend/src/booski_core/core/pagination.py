"""Keyset ("cursor") pagination shared by every list endpoint.

Responses look like ``{"items": [...], "next_cursor": "…" | null}``. Pass ``next_cursor`` back as
``?cursor=`` to get the next page. Cursors are opaque to clients; they encode the last row's sort key and
id, so pages stay stable while new rows are added (unlike offsets).
"""

import base64
import json
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Annotated, Any, Literal

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Select, SQLColumnExpression, and_, or_
from sqlalchemy.orm import Session

from booski_core.core.errors import ProblemError

DEFAULT_LIMIT = 50
MAX_LIMIT = 200

Limit = Annotated[int, Query(ge=1, le=MAX_LIMIT, description="Page size.")]
Cursor = Annotated[str | None, Query(max_length=512, description="`next_cursor` from the previous page.")]


class Page[T](BaseModel):
    items: list[T]
    next_cursor: str | None


SortValue = str | int | float | date | datetime


@dataclass(frozen=True)
class SortKey:
    """A non-null sort expression plus how to turn a cursor's JSON value back into a typed value."""

    expression: SQLColumnExpression[Any]
    decode: Callable[[Any], SortValue]
    direction: Literal["asc", "desc"] = "desc"


def _encode(value: SortValue, row_id: uuid.UUID) -> str:
    plain = value.isoformat() if isinstance(value, (date, datetime)) else value
    raw = json.dumps([plain, str(row_id)], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode(cursor: str, key: SortKey) -> tuple[SortValue, uuid.UUID]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value, row_id = json.loads(base64.urlsafe_b64decode(padded))
        return key.decode(value), uuid.UUID(row_id)
    except (ValueError, TypeError, json.JSONDecodeError):
        raise ProblemError(400, "The cursor is invalid. Start again from the first page.") from None


def paginate[R](
    db: Session,
    query: Select[R],
    *,
    key: SortKey,
    id_column: SQLColumnExpression[uuid.UUID],
    limit: int,
    cursor: str | None,
    sort_value: Callable[[R], SortValue],
    row_id: Callable[[R], uuid.UUID],
) -> tuple[Sequence[R], str | None]:
    """Applies ordering, the cursor and the limit. Returns this page's rows and the next cursor."""
    if cursor:
        value, last_id = _decode(cursor, key)
        if key.direction == "desc":
            after = or_(key.expression < value, and_(key.expression == value, id_column < last_id))
        else:
            after = or_(key.expression > value, and_(key.expression == value, id_column > last_id))
        query = query.where(after)
    ordering = (
        (key.expression.desc(), id_column.desc())
        if key.direction == "desc"
        else (key.expression.asc(), id_column.asc())
    )
    rows = db.scalars(query.order_by(*ordering).limit(limit + 1)).all()
    if len(rows) <= limit:
        return rows, None
    page = rows[:limit]
    last = page[-1]
    return page, _encode(sort_value(last), row_id(last))
