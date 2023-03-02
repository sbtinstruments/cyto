from __future__ import annotations

from typing import TypeVar

import anyio

from ._task_tree import InstanceMapping, Node, TaskData
from .current_tree import add_root_path

T = TypeVar("T")

__all__ = ["instances", "data"]


def instances() -> InstanceMapping:
    return InstanceMapping(data())


def data() -> TaskData:
    tree, path_from_root_to_node = add_root_path()
    current_task = _current_task_from_path(path_from_root_to_node)
    return TaskData(tree=tree, task=current_task)


def _current_task_from_path(path_from_root_to_node: tuple[Node, ...]) -> Node:
    assert len(path_from_root_to_node) >= 1
    current_task = path_from_root_to_node[-1]
    assert current_task == anyio.get_current_task()
    return current_task
