from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, cast

from pydantic import root_validator

from ..basic import pairwise
from ..interval import time_interval
from ..model import FrozenModel


class TrailSection(FrozenModel):
    """Subsection of an overall trail."""

    name: str
    interval: time_interval.ClosedOpenFin
    hints: frozenset[str] = frozenset()

    def remaining(self) -> timedelta:
        """Return the remaining time of this section as of now.

        Returns the entire duration of the interval if this section is in the future.
        Returns zero if this section is in the past.
        """
        now = datetime.now(timezone.utc)
        if now < self.interval.lower:
            return timedelta()
        if self.interval.upper <= now:
            return self.interval.duration()
        return self.interval.upper - now


class Trail(FrozenModel):
    """Time-sequential, linear route split into contiguous sections."""

    sections: tuple[TrailSection, ...] = tuple()

    @root_validator
    def _consecutive_sections(cls, values: dict[str, Any]) -> dict[str, Any]:
        sections = cast(tuple[TrailSection, ...], values.get("sections"))
        if len(sections) > 1:
            if not all(
                s0.interval.upper <= s1.interval.lower for s0, s1 in pairwise(sections)
            ):
                raise ValueError(
                    "We require that sections are consecutive (but not contiguous) and"
                    " without overlap"
                )
        return values

    def current_section(self) -> TrailSection | None:
        """Return the section that corresponds to the current time (if any)."""
        now = datetime.now(timezone.utc)
        for section in self.sections:
            if now in section.interval:
                return section
        return None
