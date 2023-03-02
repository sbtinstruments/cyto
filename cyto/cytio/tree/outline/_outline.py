from __future__ import annotations

from typing import Any, Optional

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from ....model import FrozenModel
from .._task_tree import TaskTree
from .._task_tree._instance_mapping import InstanceMapping
from ..section import Section, SectionHint
from ..section._mutable_section import TimeRange


class Outline(FrozenModel):
    name: str
    actual: Optional[TimeRange] = None
    planned: Optional[TimeRange] = None
    hints: frozenset[SectionHint] = frozenset()
    own_work: tuple[Outline, ...] = tuple()
    child_tasks: frozenset[Outline] = frozenset()

    # HACK: Avoid issue with combination of FrozenModel and dataclass.
    # This does not take hash collisions into account!
    def __eq__(self, rhs: Any) -> bool:
        if not isinstance(rhs, Outline):
            return NotImplemented
        return hash(self) == hash(rhs)

    @classmethod
    def from_section(
        cls,
        section: Section,
        *,
        name: Optional[str] = None,
        child_tasks: frozenset[Outline] = frozenset(),
    ) -> Outline:
        own_work = tuple(cls.from_section(child) for child in section.children)
        if name is None:
            name = section.name
        if name is None:
            raise ValueError(
                "Section must have a name (or you must provide one for it)"
            )
        return Outline(
            name=name,
            actual=section.actual,
            planned=section.planned,
            hints=section.hints,
            own_work=own_work,
            child_tasks=child_tasks,
        )

    def pretty_print(self, *, level: int = 0, prefix: str = "") -> None:
        indent = " " * level * 4
        if level == 0:
            print()
        own_line = f"{indent}{prefix}{self.name}"
        if self.hints:
            joined_hints = ", ".join(self.hints) if self.hints else None
            own_line += f" ({joined_hints})"
        print(own_line)
        if self.own_work:
            for child in self.own_work:
                child.pretty_print(level=level + 1, prefix="[S]")
        if self.child_tasks:
            for child in self.child_tasks:
                child.pretty_print(level=level + 1, prefix="[P]")

    @classmethod
    def from_tree(
        cls, tree: TaskTree, *, node: Optional[anyio.TaskInfo] = None
    ) -> Outline:
        if node is None:
            node = tree.root
        child_tasks: frozenset[Outline] = frozenset(
            cls.from_tree(tree, node=neighbour) for neighbour in tree.graph[node]
        )
        try:
            section = InstanceMapping(tree.nodes()[node])[Section]
        except KeyError:
            return Outline(name=node.name, child_tasks=child_tasks)
        return Outline.from_section(section, name=node.name, child_tasks=child_tasks)


OutlineSendStream = MemoryObjectSendStream[Outline]
OutlineReceiveStream = MemoryObjectReceiveStream[Outline]
