from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from datetime import datetime
from itertools import pairwise
from typing import Self

import portion

from ...cytio.tree import fetch
from ...model import FrozenModel
from .._project_database import Project, ProjectDatabase
from .._trail import Trail, TrailSection
from ._project_db_to_trail_config import ProjectDatabaseToTrailConfig

_LOGGER = logging.getLogger(__name__)


def project_db_to_trail(db: ProjectDatabase) -> Trail:
    """Return summary of the given project database.

    Projects may run in parallel and therefore overlap in time. In this situation,
    we must choose one project and discard the rest. We favor projects with recent
    activity.
    """
    return Trail(sections=tuple(_project_db_to_trail_sections(db)))


def _project_db_to_trail_sections(db: ProjectDatabase) -> Iterator[TrailSection]:
    config = fetch(ProjectDatabaseToTrailConfig, store_produced_instance=False)
    projects: Iterable[Project] = db.all_projects()

    if config.only_include is not None:
        projects = (
            project
            for project in projects
            if project.project_name in config.only_include
        )

    markers: list[_Marker] = []
    for project in projects:
        markers.extend(_markers(project))
    sorted_markers = sorted(markers, key=lambda m: m.time)

    stack: list[Project] = []
    for marker_first, marker_second in pairwise(sorted_markers):
        if isinstance(marker_first, _BeginMarker):
            stack.append(marker_first.project)
        elif isinstance(marker_first, _EndMarker):
            stack.pop()
        else:
            # TRY004: Normally, we prefer `TypeError` but that only applies if
            # it's an *argument* of an invalid type. In this case, `marker_first` is
            # an internal detail.
            raise RuntimeError("Unknown marker")  # noqa: TRY004
        try:
            marker_project = stack[-1]
        except IndexError:
            continue
        yield TrailSection(
            name=config.rename(marker_project.project_name),
            interval=portion.closedopen(
                lower=marker_first.time, upper=marker_second.time
            ),
            hints=marker_project.hints,
        )


def _markers(project: Project) -> Iterator[_Marker]:
    yield _BeginMarker.from_project(project)
    if (end := _EndMarker.from_project(project)) is not None:
        yield end


class _Marker(FrozenModel):
    time: datetime
    project: Project


class _BeginMarker(_Marker):
    @classmethod
    def from_project(cls, project: Project) -> Self:
        if project.actual is not None:
            time = project.actual.lower
        else:
            assert project.planned is not None
            time = project.planned.lower
        return cls(time=time, project=project)


class _EndMarker(_Marker):
    @classmethod
    def from_project(cls, project: Project) -> Self | None:
        # There is a _finite_ upper bound on the actual time spent
        if (actual_upper := _get_finite_upper(project.actual)) is not None:
            time = actual_upper
        # There is a _finite_ upper bound on the planned time
        elif (planned_upper := _get_finite_upper(project.planned)) is not None:
            time = planned_upper
        else:
            return None
        return cls(time=time, project=project)


def _get_finite_upper(interval: portion.Interval) -> datetime | None:
    if isinstance(interval, portion.Interval) and isinstance(interval.upper, datetime):
        return interval.upper
    return None
