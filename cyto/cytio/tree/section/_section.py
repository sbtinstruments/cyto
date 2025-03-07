from __future__ import annotations

from ....interval import TimeInterval
from ....model import FrozenModel
from ._mutable_section import SectionHint, _MutableSection


class Section(FrozenModel):
    name: str
    actual: TimeInterval
    planned: TimeInterval
    hints: frozenset[SectionHint] = frozenset()
    children: tuple[Section, ...] = ()

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
