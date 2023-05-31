from collections.abc import Iterator
from contextlib import contextmanager

import anyio

from ._task_tree._models import Node, NodePath
from ._task_tree._task_tree import TaskTree

# Mapping of root node to task tree
_TASK_TREES: dict[Node, TaskTree] = {}


@contextmanager
def plant_tree() -> Iterator[TaskTree]:
    current_task = anyio.get_current_task()
    if current_task is None:
        raise RuntimeError("You must call 'plant' within the context of a running task")
    if current_task in _TASK_TREES:
        raise RuntimeError(
            "Already registered a root for the current task. There can only be one."
        )
    tree = TaskTree(root=current_task)
    _TASK_TREES[current_task] = tree
    try:
        with tree:
            yield tree
    finally:
        del _TASK_TREES[current_task]


def add_root_path() -> tuple[TaskTree, tuple[Node, ...]]:
    """Add the current task (and all parent tasks) to the task tree.

    Finds the path from the current task to the root task. Adds all tasks
    on said path to the task tree.
    """
    tree, path_from_root_to_node = tree_and_root_path()
    # We convert `path_from_root_to_node` from generator to tuple because we both:
    #
    #  * Consume `path_from_root_to_node` in `add_path`.
    #  * Return `path_from_root_to_node`.
    #
    # Otherwise (if we just returned the generator), we may
    # accidentally return an exhausted generator.
    path_from_root_to_node = tuple(path_from_root_to_node)
    tree.add_path(path_from_root_to_node)
    assert len(path_from_root_to_node) >= 1, "There is at least one node in the path"
    return tree, path_from_root_to_node


def tree_and_root_path() -> tuple[TaskTree, NodePath]:
    """Return the innermost task tree associated with the current task.

    Innermost, in the sense that the closest path from the current task
    is to said tree's root node.

    Raises `RuntimeError` if there is no task tree associated with the
    current task.
    """
    path_from_node_to_root: list[Node] = []
    for node in global_root_path():
        path_from_node_to_root.append(node)
        try:
            tree = _TASK_TREES[node]
        except KeyError:
            continue
        path_from_root_to_node = reversed(path_from_node_to_root)
        return (tree, path_from_root_to_node)
    raise RuntimeError("There isn't a path from the current task to a root node")


def global_root_path() -> Iterator[Node]:
    """Return all tasks from the current task to the root task (both inclusive).

    This function assumes a structured task hierarchy. E.g., a task hierarchy
    created from nested task groups (see `anyio.create_task_group`).

    Note that this tasks runs in worst-case O(N) where N is the number
    of running tasks.
    """
    task = anyio.get_current_task()
    # TODO: Implement "fast path" that search `task.id` and `task.parent_id`
    # before we call the "expensive" `get_running_tasks` method.
    all_tasks = anyio.get_running_tasks()
    tasks_by_id = {task.id: task for task in all_tasks}
    while True:
        yield task
        if task.parent_id is None:
            # We reached the root task.
            break
        try:
            task = tasks_by_id[task.parent_id]
        except KeyError as exc:
            raise RuntimeError(
                "Broken task graph: Found a task that's not in the list of running"
                " tasks."
            ) from exc
