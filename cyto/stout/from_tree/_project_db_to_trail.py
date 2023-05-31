from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime
from itertools import pairwise

from ...cytio.tree import fetch
from ...interval import time_interval
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
    config = fetch(ProjectDatabaseToTrailConfig)
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
            name=marker_project.project_name,
            interval=time_interval.ClosedOpenFin(
                lower=marker_first.time, upper=marker_second.time
            ),
            hints=marker_project.hints,
        )


def _markers(project: Project) -> Iterator[_Marker]:
    yield _BeginMarker.from_project(project)
    if (end := _EndMarker.from_project(project)) is not None:
        yield end


@dataclass(frozen=True)
class _Marker:
    time: datetime
    project: Project


# For some reason, pylint fails to see that the `_Marker`-derived
# classes are dataclasses.
class _BeginMarker(_Marker):  # pylint: disable=too-few-public-methods
    @classmethod
    def from_project(cls, project: Project) -> _BeginMarker:
        if project.actual is not None:
            time = project.actual.lower
        else:
            assert project.planned is not None
            time = project.planned.lower
        return cls(time=time, project=project)


class _EndMarker(_Marker):  # pylint: disable=too-few-public-methods
    @classmethod
    def from_project(cls, project: Project) -> _EndMarker | None:
        if isinstance(project.actual, time_interval.ClosedOpenFin):
            time = project.actual.upper
        elif isinstance(project.planned, time_interval.ClosedOpenFin):
            time = project.planned.upper
        else:
            return None
        return cls(time=time, project=project)
