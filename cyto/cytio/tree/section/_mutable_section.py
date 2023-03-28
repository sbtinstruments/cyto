from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import TracebackType
from typing import Iterable, Iterator, Literal, Optional

from pydantic import BaseModel, Field

from ....interval import time_interval

SectionHint = Literal["may-end-early", "indeterminate-indicator"]


class _MutableSection(BaseModel):
    name: str
    actual: time_interval.ClosedOpen = Field(
        default_factory=lambda: time_interval.closed_open(
            lower=datetime.now(timezone.utc)
        )
    )
    planned_duration: Optional[timedelta] = None
    hints: set[SectionHint] = Field(default_factory=set)
    children: dict[str, _MutableSection] = Field(default_factory=dict)
    active_child: Optional[_MutableSection] = None

    @property
    def planned(self) -> time_interval.ClosedOpen:
        assert self.actual is not None
        lower = self.actual.lower
        upper = (
            lower + self.planned_duration if self.planned_duration is not None else None
        )
        return time_interval.closed_open(lower, upper)

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
        self.actual = time_interval.closed_open(
            self.actual.lower, datetime.now(timezone.utc)
        )
