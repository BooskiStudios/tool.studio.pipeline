"""Alembic environment. Use ``booski db upgrade`` (or ``alembic`` from ``backend/``) to run migrations."""

from alembic import context
from sqlalchemy import create_engine, pool

from booski_core.config import get_settings
from booski_core.models import Base

config = context.config
target_metadata = Base.metadata


def _database_url() -> str:
    url = config.attributes.get("database_url")
    return str(url) if url else get_settings().sqlalchemy_url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
