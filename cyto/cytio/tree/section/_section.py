from __future__ import annotations

from typing import Optional

from ....model import FrozenModel
from ._mutable_section import SectionHint, TimeRange, _MutableSection


class Section(FrozenModel):
    name: Optional[str] = None
    actual: TimeRange
    planned: TimeRange
    hints: frozenset[SectionHint] = frozenset()
    children: tuple[Section, ...] = tuple()

    @classmethod
    def from_mutable_section(cls, mutable_section: _MutableSection) -> Section:
        return cls(
            name=mutable_section.name,
            actual=mutable_section.actual,
            planned=mutable_section.planned,
            hints=mutable_section.hints,
            children=(
                cls.from_mutable_section(child)
                for child in mutable_section.children.values()
            ),
        )

    def pretty_print(self, *, level: int = 0) -> None:
        indent = " " * level * 4
        if level == 0:
            print()
        print(f"{indent}{self.name}")
        for child in self.children:
            child.pretty_print(level=level + 1)
