"""Small helpers for building response models from ORM objects."""

from typing import Any

from pydantic import BaseModel


def attributes(record: object, model: type[BaseModel]) -> dict[str, Any]:
    """The record's attributes that ``model`` declares (skips computed fields the record doesn't have)."""
    return {name: getattr(record, name) for name in model.model_fields if hasattr(record, name)}
