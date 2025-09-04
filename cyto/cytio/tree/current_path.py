from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from contextlib import suppress
from typing import Any, TypeVar

from ._task_tree import InstanceMapping, Node, TaskTree
from .current_tree import add_root_path

T = TypeVar("T")

_LOGGER = logging.getLogger(__name__)


def get_first_instance[T](type_: type[T]) -> T:
    """Get the first instance (if any) of the given type for the current task path.

    Traverses the task path from the current task to the root task. Returns the first
    instance of the given type.

    Raises `LookupError` if there is no instance for the given type.
    """
    for instance in get_instances(type_):
        return instance
    raise LookupError


def get_instances[T](type_: type[T]) -> Iterable[T]:
    """Get all instances (if any) of the given type for the current task path.

    Traverses the task path from the current task to the root task. Returns instances
    in that order.
    """
    tree, path_from_root_to_node = add_root_path()
    path_data = _path_data(tree, path_from_root_to_node)
    path_instances = _path_instances(path_data, type_)
    instances = list(path_instances)
    return reversed(instances)


def _path_instances[T](
    path_data: Iterable[dict[Any, Any]], type_: type[T]
) -> Iterator[T]:
    for node_data in path_data:
        node_instances = InstanceMapping(node_data)
        with suppress(KeyError):
            yield node_instances[type_]


def _path_data(tree: TaskTree, path: Iterable[Node]) -> Iterator[dict[Any, Any]]:
    nodes = tree.nodes()
    for node in path:
        try:
            node_data = nodes[node]
        except KeyError as exc:
            raise RuntimeError("Tree must contain all nodes in the path") from exc
        assert isinstance(node_data, dict)
        yield node_data
