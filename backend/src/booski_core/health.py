"""Liveness and readiness checks. These are the only routes in PR 2.1 and need no authentication."""

import logging
from typing import Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from booski_core.migrations_config import database_revisions, migration_heads

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger("booski_core.health")


class Liveness(BaseModel):
    status: Literal["ok"]


class Readiness(BaseModel):
    status: Literal["ok", "unavailable"]
    database: Literal["ok", "unreachable"]
    migrations: Literal["head", "behind", "unknown"]


@router.get("/live", response_model=Liveness)
def live() -> Liveness:
    """The process is running. Says nothing about the database."""
    return Liveness(status="ok")


@router.get("/ready", response_model=Readiness, responses={503: {"model": Readiness}})
def ready(request: Request, response: Response) -> Readiness:
    """The database is reachable and its schema matches this version of the code."""
    engine: Engine = request.app.state.engine
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        applied = database_revisions(engine)
    except SQLAlchemyError:
        # Log the cause for operators; never return connection details to the caller.
        logger.warning("Readiness check: database unreachable", exc_info=True)
        response.status_code = 503
        return Readiness(status="unavailable", database="unreachable", migrations="unknown")

    if applied != migration_heads():
        response.status_code = 503
        return Readiness(status="unavailable", database="ok", migrations="behind")
    return Readiness(status="ok", database="ok", migrations="head")
