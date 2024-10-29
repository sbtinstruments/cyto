from __future__ import annotations

from collections.abc import AsyncIterable
from contextlib import AbstractAsyncContextManager
from datetime import timedelta

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

    def has_hint(self, hint: str) -> bool:
        """Current section (if any) has the given hint."""
        if self.trail is None:
            return False
        section = self.trail.current_section()
        if section is None:
            return False
        return hint in section.hints

    def time_remaining(self) -> timedelta | None:
        """Return time remaining in the current section (if any)."""
        if self.trail is None:
            return None
        section = self.trail.current_section()
        if section is None:
            return None
        return section.remaining()

    def current_name(self) -> str | None:
        """Return name of the current section (if any)."""
        if self.trail is None:
            return None
        section = self.trail.current_section()
        if section is None:
            return None
        return section.name


OutlineStream = AbstractAsyncContextManager[AsyncIterable[Outline]]
