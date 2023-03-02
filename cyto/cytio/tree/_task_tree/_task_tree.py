from __future__ import annotations

from contextlib import AbstractContextManager, contextmanager
from types import TracebackType
from typing import Iterator, Optional

import networkx as nx
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from networkx.classes.reportviews import NodeDataView, NodeView

from ....basic import pairwise
from ...broadcast import BroadcastValue
from ._models import Node, NodePath
from ._task_data import TaskData

TreeSendStream = MemoryObjectSendStream["TaskTree"]
TreeReceiveStream = MemoryObjectReceiveStream["TaskTree"]


class TaskTree(AbstractContextManager["TaskTree"]):
    """Tree in the task graph rooted at a given node.

    Technically, the underlying graph is a *directed rooted tree*. Specifically,
    an *arborescence* or *out-tree*.

    See:
     * https://en.wikipedia.org/wiki/Tree_(graph_theory)#Rooted_tree
     * https://en.wikipedia.org/wiki/Arborescence_(graph_theory)
    """

    def __init__(self, *, root: Node) -> None:
        self._graph = nx.DiGraph()
        self._graph.add_node(root)
        self._root = root
        self._change_broadcast: BroadcastValue[TaskTree] = BroadcastValue(self)

    def subscribe_to_changes(self) -> TreeReceiveStream:
        return self._change_broadcast.subscribe()

    @property
    def graph(self) -> nx.DiGraph:
        return self._graph.copy(as_view=True)

    @property
    def root(self) -> Node:
        return self._root

    @property
    def name_graph(self) -> nx.DiGraph:
        return nx.relabel_nodes(self._graph, lambda n: n.name)

    def data_for_task(self, node: Node) -> TaskData:
        return TaskData(tree=self, task=node)

    def nodes(self) -> NodeDataView:
        """Return immutable view of the nodes in this task tree."""
        # TODO: Actually make the view (faux-) immutable
        return self._graph.nodes.data(data=True)

    @contextmanager
    def mutate_nodes(self) -> Iterator[NodeView]:
        """Return mutable view of the nodes in this task tree.

        Note that while you can't add/delete nodes via the returned `NodeView`,
        you *can* change the user data of the nodes themselves.

        Pushes changes on exit.
        """
        try:
            yield self._graph.nodes
        finally:
            self._broadcast_change()

    def add_path(self, path_from_root_to_node: NodePath) -> None:
        # Early out if the path is already in this graph.
        # This way, we avoid unnecessary calls to `_push_change`
        if nx.is_path(self._graph, path_from_root_to_node):
            return
        self._graph.add_edges_from(pairwise(path_from_root_to_node))
        if not nx.is_arborescence(self._graph):
            raise RuntimeError("No longer an arborescence")
        self._broadcast_change()

    def pretty_print(self, *, node: Optional[Node] = None, level: int = 0) -> None:
        if node is None:
            node = self._root
        indent = " " * level * 4
        print(f"{indent}{node.name}")
        for neighbour in self._graph[node]:
            self.pretty_print(node=neighbour, level=level + 1)

    def _broadcast_change(self) -> None:
        self._change_broadcast.set(self)

    def __enter__(self) -> TaskTree:
        self._broadcast_change()
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self._change_broadcast.__exit__(exc_type, exc_value, traceback)
