from __future__ import annotations

from collections.abc import Hashable, Iterator, MutableMapping
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from ._models import Node

if TYPE_CHECKING:
    from ._task_tree import TaskTree


class TaskData(MutableMapping[Any, Any]):
    """View of task data."""

    def __init__(self, *, tree: TaskTree, task: Node) -> None:
        self._tree = tree
        self._task = task
        if self._task not in self._tree.nodes():
            raise ValueError("Task must be part of the task tree")

    def __getitem__(self, key: Hashable) -> Any:
        node = self._current_node()
        return node[key]

    def __setitem__(self, key: Hashable, value: Any) -> None:
        with self._mutate_current_node() as node:
            node[key] = value

    def __delitem__(self, key: Hashable) -> None:
        with self._mutate_current_node() as node:
            del node[key]

    def __iter__(self) -> Iterator[Hashable]:
        return iter(self._tree.nodes())

    def __len__(self) -> int:
        return len(self._tree.nodes())

    @contextmanager
    def _mutate_current_node(self) -> Iterator[dict[Any, Any]]:
        with self._tree.mutate_nodes() as nodes:
            # We know that `current_task` is in the task tree, so there is no need
            # for a `try..except KeyError` block
            node = nodes[self._task]
            assert isinstance(node, dict)
            yield node

    def _current_node(self) -> dict[Any, Any]:
        nodes = self._tree.nodes()
        # We know that `current_task` is in the task tree, so there is no need
        # for a `try..except KeyError` block
        node = nodes[self._task]
        assert isinstance(node, dict)
        return node
