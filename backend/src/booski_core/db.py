"""Database engine, sessions and the declarative ``Base`` shared by every module's models."""

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine, MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from booski_core.config import Settings

# Deterministic constraint names, so Alembic migrations can drop and rename them reliably.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for all ORM models. Import model modules in ``booski_core.models`` so Alembic sees them."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def create_db_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.sqlalchemy_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": settings.database_connect_timeout_seconds},
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_session(request: Request) -> Iterator[Session]:
    """FastAPI dependency: one session per request, rolled back if the request fails."""
    factory: sessionmaker[Session] = request.app.state.session_factory
    with factory() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
