from collections.abc import Iterable

import anyio

Node = anyio.TaskInfo
NodePath = Iterable[Node]
