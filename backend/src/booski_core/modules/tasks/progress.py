"""Progress computed from real tasks: the share of live, non-cancelled tasks that are done.

No weighting or scoring: a milestone or project with no tasks reports 0 of 0.
"""

import uuid
from collections.abc import Iterable

from pydantic import BaseModel
from sqlalchemy import SQLColumnExpression, func, select
from sqlalchemy.orm import Session

from booski_core.modules.tasks.models import Task


class Progress(BaseModel):
    total: int
    done: int
    percent: int  # 0-100, rounded down


def _progress(total: int, done: int) -> Progress:
    return Progress(total=total, done=done, percent=(done * 100 // total) if total else 0)


def _counts(
    db: Session, column: SQLColumnExpression[uuid.UUID | None], ids: Iterable[uuid.UUID]
) -> dict[uuid.UUID, Progress]:
    id_list = list(ids)
    if not id_list:
        return {}
    rows = db.execute(
        select(column, func.count(), func.count().filter(Task.status == "done"))
        .where(column.in_(id_list), Task.archived_at.is_(None), Task.status != "cancelled")
        .group_by(column)
    ).all()
    found = {row[0]: _progress(row[1], row[2]) for row in rows}
    return {i: found.get(i, _progress(0, 0)) for i in id_list}


def project_progress(db: Session, project_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, Progress]:
    return _counts(db, Task.project_id, project_ids)


def milestone_progress(db: Session, milestone_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, Progress]:
    return _counts(db, Task.milestone_id, milestone_ids)
