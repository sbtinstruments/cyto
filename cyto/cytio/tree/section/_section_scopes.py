from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Iterable, Iterator
from contextlib import ExitStack, asynccontextmanager, contextmanager
from datetime import timedelta

import anyio

from ... import _scopes
from ..current_task import instances
from ._mutable_section import SectionHint, _MutableSection
from ._section import Section

_LOGGER = logging.getLogger(__name__)


@contextmanager
def warn_after(time_limit: float | timedelta) -> Iterator[None]:
    time_limit = _normalize_timedelta(time_limit)
    try:
        task_section = instances()[_MutableSection]
    except KeyError as exc:
        raise RuntimeError("Can't use 'warn_after' outside a section context") from exc
    current_section = task_section.innermost_active_child()

    if current_section.planned_duration is not None:
        raise RuntimeError("Can't use multiple timing scopes within a section context")

    current_section.hints.add("may-end-early")
    current_section.planned_duration = time_limit

    # Trigger update
    instances().setauto(Section.from_mutable_section(task_section))

    with _scopes.warn_after(time_limit, logger=_LOGGER):
        yield


@contextmanager
def fail_after(time_limit: float | timedelta) -> Iterator[None]:
    time_limit = _normalize_timedelta(time_limit)
    try:
        task_section = instances()[_MutableSection]
    except KeyError as exc:
        raise RuntimeError("Can't use 'fail_after' outside a section context") from exc
    current_section = task_section.innermost_active_child()

    if current_section.planned_duration is not None:
        raise RuntimeError("Can't use multiple timing scopes within a section context")

    current_section.hints.add("may-end-early")
    current_section.planned_duration = time_limit

    # Trigger update
    instances().setauto(Section.from_mutable_section(task_section))

    with anyio.fail_after(time_limit.total_seconds()):
        yield


@asynccontextmanager
async def wait_exactly(
    time_limit: float | timedelta, *, shield: bool = False
) -> AsyncIterator[None]:
    time_limit = _normalize_timedelta(time_limit)
    try:
        task_section = instances()[_MutableSection]
    except KeyError as exc:
        raise RuntimeError(
            "Can't use 'wait_exactly' outside a section context"
        ) from exc
    current_section = task_section.innermost_active_child()

    if current_section.planned_duration is not None:
        raise RuntimeError("Can't use multiple timing scopes within a section context")

    current_section.hints.add("may-end-early")
    current_section.planned_duration = time_limit

    # Trigger update
    instances().setauto(Section.from_mutable_section(task_section))

    async with _scopes.wait_exactly(time_limit, shield=shield):
        yield


async def sleep(time_limit: float | timedelta) -> None:
    time_limit = _normalize_timedelta(time_limit)
    try:
        task_section = instances()[_MutableSection]
    except KeyError as exc:
        raise RuntimeError("Can't use 'sleep' outside a section context") from exc
    current_section = task_section.innermost_active_child()

    if current_section.planned_duration is not None:
        raise RuntimeError("Can't 'sleep' twice within a section context")

    current_section.planned_duration = time_limit

    # Trigger update
    instances().setauto(Section.from_mutable_section(task_section))

    await anyio.sleep(time_limit.total_seconds())


@contextmanager
def section(name: str, *, hints: Iterable[SectionHint] | None = None) -> Iterator[None]:
    """Create a new section in the current task."""
    if hints is None:
        hints = set()
    try:
        task_section = instances()[_MutableSection]
        is_root_section = False
    except KeyError:
        task_section = _MutableSection(name=name, hints=hints)
        instances().setauto(task_section)
        is_root_section = True
    with ExitStack() as stack:
        if not is_root_section:
            current_section = task_section.innermost_active_child()
            stack.enter_context(current_section.child(name, hints=hints))
        instances().setauto(Section.from_mutable_section(task_section))
        yield
    instances().setauto(Section.from_mutable_section(task_section))


def _normalize_timedelta(value: timedelta | float | int) -> timedelta:
    if isinstance(value, timedelta):
        return value
    if isinstance(value, float | int):
        return timedelta(seconds=value)
    raise TypeError(f"Can't normalize {value} as timedelta.")
