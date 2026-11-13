"""Builds Alembic configuration in code, so migrations work from any working directory and inside Docker."""

from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def alembic_config(database_url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.set_main_option("file_template", "%%(rev)s_%%(slug)s")
    # Passed as an attribute rather than an ini option, so '%' in passwords needs no escaping.
    config.attributes["database_url"] = database_url
    return config


def migration_heads() -> set[str]:
    """Revision ids at the head of the migration scripts shipped with this code."""
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    return set(ScriptDirectory.from_config(config).get_heads())


def database_revisions(engine: Engine) -> set[str]:
    """Revision ids currently applied to the database (empty if never migrated)."""
    with engine.connect() as connection:
        return set(MigrationContext.configure(connection).get_current_heads())
