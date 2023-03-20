from __future__ import annotations

from typing import Iterable

from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from tinydb.database import TinyDB
from tinydb.storages import MemoryStorage

from ...interval import time_interval
from ...model import FrozenModel


class Project(FrozenModel):
    project_name: str  # Primary key
    assignee_id: int  # ID of a task/worker/thread/process/etc.
    assignee_name: str | None = None  # Name of a task/worker/thread/process/etc.
    actual: time_interval.ClosedOpen | None = None
    planned: time_interval.ClosedOpen | None = None
    hints: frozenset[str] = frozenset()
    parent: int | None = None  # Foreign key to another project


class ProjectDatabase:
    """Multi-lane time schedule for apps with parallel execution.

    See the `Trail` type for a simpler, single-lane alternative.
    """

    def __init__(self) -> None:
        self._db = TinyDB(storage=MemoryStorage)

    def add_project(self, project: Project) -> int:
        doc_id = self._db.insert(project.dict())
        assert isinstance(doc_id, int)
        return doc_id

    def all(self) -> Iterable[Project]:
        return (Project(**doc) for doc in self._db)


GanttChartSendStream = MemoryObjectSendStream[ProjectDatabase]
GanttChartReceiveStream = MemoryObjectReceiveStream[ProjectDatabase]
