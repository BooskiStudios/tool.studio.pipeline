"""Single import point for every ORM model, so ``Base.metadata`` is complete for Alembic.

Each module adds an import here when it gains tables (PR 2.2 onwards). There are no tables yet.
"""

from booski_core.db import Base

__all__ = ["Base"]
