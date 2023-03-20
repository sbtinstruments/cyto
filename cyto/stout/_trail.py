from __future__ import annotations

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
