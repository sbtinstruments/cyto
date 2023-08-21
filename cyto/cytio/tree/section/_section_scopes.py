from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Iterable, Iterator
from contextlib import AbstractContextManager, asynccontextmanager, contextmanager
from datetime import timedelta

import anyio

from ... import _scopes
from ..current_task import instances
from ._mutable_section import SectionHint, _MutableSection
from ._update_section import update_section

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
    update_section()

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
    update_section()

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
    update_section()

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
    update_section()

    await anyio.sleep(time_limit.total_seconds())


@contextmanager
def section(name: str, *, hints: Iterable[SectionHint] | None = None) -> Iterator[None]:
    """Create a new section in the current task."""
    if hints is None:
        hints = set()

    new_section: AbstractContextManager[_MutableSection]
    try:
        # Get the existing section for this task (if any)
        task_section = instances()[_MutableSection]
    except KeyError:
        # There is no existing section for this task. We create one.
        task_section = _MutableSection(name=name, hints=hints)
        instances().setauto(task_section)
        new_section = task_section
    else:
        # Early out
        if not task_section.is_entered:
            raise RuntimeError(
                "The current task already has a root-level section called "
                f"'{task_section.name}'. You tried to create a new root-level "
                f"section with name '{name}'. That would override the existing "
                "root-level section so we do not allow this. Did you mean to "
                "create a nested section instead?"
            )
        # There is an existing section for this task. We use the existing section
        # hierarchy.
        parent_section = task_section.innermost_active_child()
        new_section = parent_section.child(name, hints=hints)

    try:
        with new_section:
            update_section()
            yield
    finally:
        # Second update after `_MutableSeciton.__exit__` with, e.g., the `actual`
        # timings in place.
        update_section()


def _normalize_timedelta(value: timedelta | float | int) -> timedelta:
    if isinstance(value, timedelta):
        return value
    if isinstance(value, float | int):
        return timedelta(seconds=value)
    raise TypeError(f"Can't normalize {value} as timedelta.")
