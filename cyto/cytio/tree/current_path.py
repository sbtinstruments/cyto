from __future__ import annotations

from typing import Any, Iterable, Iterator, TypeVar

from ...model import FrozenModel
from ._task_tree import InstanceMapping, Node, TaskTree
from .current_tree import add_root_path

T = TypeVar("T", bound=FrozenModel)


def get_model(type_: type[T]) -> T:
    tree, path_from_root_to_node = add_root_path()
    path_data = _path_data(tree, path_from_root_to_node)
    path_instances = _path_instances(path_data, type_)

    model_stack = list(path_instances)
    model_stack.reverse()

    # TODO: Merge the models together.
    # For now, we just return the innermost (closest to the current task)
    # model.
    try:
        return model_stack.pop()
    except IndexError as exc:
        # HACK: For compatibility with `provide`. E.g., so that `get_model`
        # raises the same exceptions as `CurrentTaskData.get`.
        raise KeyError from exc


def _path_instances(path_data: Iterable[dict[Any, Any]], type_: type[T]) -> Iterator[T]:
    for node_data in path_data:
        node_instances = InstanceMapping(node_data)
        try:
            yield node_instances[type_]
        except KeyError:
            pass


def _path_data(tree: TaskTree, path: Iterable[Node]) -> Iterator[dict[Any, Any]]:
    nodes = tree.nodes()
    for node in path:
        try:
            node_data = nodes[node]
        except KeyError as exc:
            raise RuntimeError("Tree must contain all nodes in the path") from exc
        assert isinstance(node_data, dict)
        yield node_data
