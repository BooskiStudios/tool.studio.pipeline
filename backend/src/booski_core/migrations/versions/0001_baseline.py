"""Baseline: confirm the server is PostgreSQL 18+. No tables yet; they arrive with PR 2.2.

Revision ID: 0001
Revises:
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MINIMUM_SERVER_VERSION = 180000  # PostgreSQL 18: native uuidv7() is used for primary keys (decision D4).


def upgrade() -> None:
    version = int(op.get_bind().execute(sa.text("SHOW server_version_num")).scalar_one())
    if version < MINIMUM_SERVER_VERSION:
        raise RuntimeError(
            f"Booski Core needs PostgreSQL 18 or newer, but this server reports version {version}. "
            "Use the postgres service from docker-compose.yml."
        )


def downgrade() -> None:
    pass
