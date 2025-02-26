from __future__ import annotations

from collections.abc import Iterable

from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from tinydb.database import TinyDB
from tinydb.storages import MemoryStorage

from ...interval import TimeInterval
from ...model import FrozenModel


class Project(FrozenModel):
    project_name: str  # Primary key
    assignee_id: int  # ID of a task/worker/thread/process/etc.
    assignee_name: str | None = None  # Name of a task/worker/thread/process/etc.
    actual: TimeInterval | None = None
    planned: TimeInterval | None = None
    hints: frozenset[str] = frozenset()
    parent: int | None = None  # Foreign key to another project


class ProjectDatabase:
    """Multi-lane time schedule for apps with parallel execution.

    See the `Trail` type for a simpler, single-lane alternative.
    """

    def __init__(self) -> None:
        self._db = TinyDB(storage=MemoryStorage)

    def add_project(self, project: Project) -> int:
        doc_id = self._db.insert(project.model_dump())
        assert isinstance(doc_id, int)
        return doc_id

    def all_projects(self) -> Iterable[Project]:
        return (Project(**doc) for doc in self._db)


GanttChartSendStream = MemoryObjectSendStream[ProjectDatabase]
GanttChartReceiveStream = MemoryObjectReceiveStream[ProjectDatabase]
