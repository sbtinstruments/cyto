from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta
from types import TracebackType
from typing import Iterable, Iterator, Literal, Optional

from pydantic import BaseModel, Field

from ....model import FrozenModel

SectionHint = Literal["may-end-early", "indeterminate-indicator"]


# TODO: Consolidate this
class TimeRange(FrozenModel):
    begin_at: datetime
    end_at: Optional[datetime]


class _MutableSection(BaseModel):
    name: Optional[str] = None
    actual: TimeRange = Field(
        default_factory=lambda: TimeRange(begin_at=datetime.now())
    )
    planned_duration: Optional[timedelta] = None
    hints: set[SectionHint] = Field(default_factory=set)
    children: dict[str, _MutableSection] = Field(default_factory=dict)
    active_child: Optional[_MutableSection] = None

    @property
    def planned(self) -> TimeRange:
        assert self.actual is not None
        begin_at = self.actual.begin_at
        end_at = (
            begin_at + self.planned_duration
            if self.planned_duration is not None
            else None
        )
        return TimeRange(begin_at=begin_at, end_at=end_at)

    def innermost_active_child(self) -> _MutableSection:
        if self.active_child is not None:
            return self.active_child.innermost_active_child()
        return self

    @contextmanager
    def child(
        self,
        name: str,
        *,
        planned_duration: Optional[timedelta] = None,
        hints: Optional[Iterable[SectionHint]] = None,
    ) -> Iterator[_MutableSection]:
        if hints is None:
            hints = set()
        if self.active_child is not None:
            raise RuntimeError("There already is an active child")
        if name in self.children:
            raise ValueError("Section name already in use")
        child = _MutableSection(
            name=name, planned_duration=planned_duration, hints=hints
        )
        self.children[name] = child
        self.active_child = child
        try:
            with child:
                yield child
        finally:
            self.active_child = None

    def __enter__(self) -> _MutableSection:
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        assert self.actual is not None
        self.actual = self.actual.update(end_at=datetime.now())
