"""Optimistic concurrency for editable records (see ``db.Versioned``)."""

from booski_core.core.errors import ProblemError
from booski_core.db import Versioned


def check_version(record: Versioned, expected: int | None) -> None:
    """Rejects the change if the caller edited an out-of-date copy. ``None`` means "don't check"."""
    if expected is not None and expected != record.version:
        raise ProblemError(
            409,
            "This was changed by someone else since you loaded it. Reload and try again.",
            current_version=record.version,
        )


def bump_version(record: Versioned) -> None:
    record.version += 1
