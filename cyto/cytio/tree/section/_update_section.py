from ..current_task import instances
from ._mutable_section import _MutableSection
from ._section import Section


def update_section() -> None:
    # Get the section for the current task (if any)
    try:
        task_section = instances()[_MutableSection]
    except KeyError:
        return
    # Update the public (and immutable) counterpart called `Section`. The
    # `_MutableSection` class is just a private implementation detail that
    # we use under the hood.
    instances().setauto(Section.from_mutable_section(task_section))
