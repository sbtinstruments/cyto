from __future__ import annotations

from collections.abc import AsyncIterable
from contextlib import AbstractAsyncContextManager
from typing import Any, ClassVar

from pydantic import ConfigDict

from ..model import FrozenModel
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


OutlineStream = AbstractAsyncContextManager[AsyncIterable[Outline]]
