from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from inspect import Parameter
from typing import Iterator, Optional

from ....basic import pairwise
from ....factory import FACTORY
from ....model import FrozenModel
from .._provide import provide
from ..section._section import SectionHint
from ._outline import Outline

_LOGGER = logging.getLogger(__name__)


class TimeRange(FrozenModel):
    begin_at: datetime
    end_at: Optional[datetime]


@dataclass(frozen=True)
class SummarySegment:
    name: str
    begin_at: datetime
    end_at: datetime
    hints: frozenset[SectionHint] = frozenset()

    def __post_init__(self) -> None:
        if self.begin_at > self.end_at:
            raise ValueError("Segment ends before it begins")


class OutlineSummaryConfig(FrozenModel):
    only_include: Optional[frozenset[str]] = None


@dataclass(frozen=True)
class OutlineSummary:
    segments: tuple[SummarySegment, ...]

    def __post_init__(self) -> None:
        if len(self.segments) > 1:
            if not all(s0.end_at <= s1.begin_at for s0, s1 in pairwise(self.segments)):
                print(f"{self.segments=}")
                raise ValueError(
                    "We require that segments are consecutive (but not contiguous) and"
                    " without overlap"
                )

    @classmethod
    def from_outline(cls, outline: Outline) -> OutlineSummary:
        """Return summary of the given outline.

        Recursively visits all children and produces flattened overview based
        on recent activity.
        """
        segments = _summary_segments(outline)
        return OutlineSummary(segments=tuple(segments))


def _summary_segments(outline: Outline) -> Iterator[SummarySegment]:
    config = provide(OutlineSummaryConfig)

    outlines = flatten(outline)
    if config.only_include is not None:
        outlines = (
            outline for outline in outlines if outline.name in config.only_include
        )

    markers: list[_Marker] = []
    for outline_ in outlines:
        markers.extend(_markers(outline_))
    sorted_markers = sorted(markers, key=lambda m: m.time)

    stack: list[Outline] = []
    for marker_first, marker_second in pairwise(sorted_markers):
        if isinstance(marker_first, _BeginMarker):
            stack.append(marker_first.outline)
        elif isinstance(marker_first, _EndMarker):
            stack.pop()
        else:
            raise RuntimeError("Unknown marker")
        try:
            marker_outline = stack[-1]
        except IndexError:
            continue
        yield SummarySegment(
            name=marker_outline.name,
            begin_at=marker_first.time,
            end_at=marker_second.time,
            hints=marker_outline.hints,
        )
        # # The "persist" hint basically means: This is the last segment so
        # # don't show the rest (if any). We use it as a hack to avoid an
        # # unwanted transition from "Emptying" to "Measuring" and the very
        # # end of the measure program.
        # if "persist" in marker_outline.hints:
        #     return


def _markers(outline: Outline) -> Iterator[_Marker]:
    yield _BeginMarker.from_outline(outline)
    if (end := _EndMarker.from_outline(outline)) is not None:
        yield end


def flatten(outline: Outline) -> Iterator[Outline]:
    yield outline
    for child in outline.own_work:
        yield from flatten(child)
    # for child in outline.child_tasks:
    #    yield from flatten(child)


@dataclass(frozen=True)
class _Marker:
    time: datetime
    outline: Outline


# For some reason, pylint fails to see that the `_Marker`-derived
# classes are dataclasses.
class _BeginMarker(_Marker):  # pylint: disable=too-few-public-methods
    @classmethod
    def from_outline(cls, outline: Outline) -> _BeginMarker:
        if outline.actual is not None:
            time = outline.actual.begin_at
        else:
            assert outline.planned is not None
            time = outline.planned.begin_at
        return cls(time=time, outline=outline)


class _EndMarker(_Marker):  # pylint: disable=too-few-public-methods
    @classmethod
    def from_outline(cls, outline: Outline) -> Optional[_EndMarker]:
        if outline.actual is not None and outline.actual.end_at is not None:
            time = outline.actual.end_at
        elif outline.planned is not None and outline.planned.end_at is not None:
            time = outline.planned.end_at
        else:
            return None
        return cls(time=time, outline=outline)


def _outline_summary_config_factory(param: Parameter) -> OutlineSummaryConfig:
    if param.annotation is not OutlineSummaryConfig:
        raise ValueError
    return OutlineSummaryConfig()


FACTORY.add_factory(_outline_summary_config_factory)
