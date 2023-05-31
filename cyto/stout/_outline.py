from __future__ import annotations

from collections.abc import AsyncIterable
from contextlib import AbstractAsyncContextManager
from typing import Any

from ..model import FrozenModel, none_as_null
from ._trail import Trail


class Outline(FrozenModel):
    """Plan (past, present, and future) for an execution.

    For now, we support:

     * The simple, single-lane `Trail` (for apps with serial execution).
     * TODO: The complex, multi-lane `ProjectDatabase` (for apps with parallel
       execution).

    We may add more types to this list in the future.
    """

    trail: Trail | None = None

    class Config:
        """pydantic uses this class for model-local configuration."""

        @staticmethod
        def schema_extra(schema: dict[str, Any], model: type[Outline]) -> None:
            """Ensure that `Optional` results in a nullable type in the schema."""
            none_as_null(schema, model)


OutlineStream = AbstractAsyncContextManager[AsyncIterable[Outline]]
