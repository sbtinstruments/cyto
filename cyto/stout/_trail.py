from __future__ import annotations

from datetime import UTC, datetime, timedelta
from itertools import pairwise
from typing import Self

from pydantic import model_validator

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
        now = datetime.now(UTC)
        if now < self.interval.lower:
            return timedelta()
        if self.interval.upper <= now:
            return self.interval.duration()
        return self.interval.upper - now


class Trail(FrozenModel):
    """Time-sequential, linear route split into contiguous sections."""

    sections: tuple[TrailSection, ...] = ()

    @model_validator(mode="after")
    def _consecutive_sections(self) -> Self:
        if len(self.sections) > 1 and not all(
            s0.interval.upper <= s1.interval.lower for s0, s1 in pairwise(self.sections)
        ):
            raise ValueError(
                "We require that sections are consecutive (but not contiguous) and"
                " without overlap"
            )
        return self

    def current_section(self) -> TrailSection | None:
        """Return the section that corresponds to the current time (if any)."""
        now = datetime.now(UTC)
        for section in self.sections:
            if now in section.interval:
                return section
        return None
