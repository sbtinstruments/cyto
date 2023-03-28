import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import anyio

from ...cytio.broadcast import BroadcastValue
from ...cytio.tree import TreeReceiveStream
from .._outline import Outline
from ._project_db_to_trail import project_db_to_trail
from ._tree_to_project_db import tree_to_project_database

_LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def tree_changes_to_outline(
    tree_change_stream: TreeReceiveStream,
) -> AsyncIterator[BroadcastValue[Outline]]:
    outline_broadcast: BroadcastValue[Outline] = BroadcastValue()
    with outline_broadcast:
        async with anyio.create_task_group() as tg:
            tg.start_soon(
                _tree_changes_to_outline, tree_change_stream, outline_broadcast
            )
            yield outline_broadcast
            tg.cancel_scope.cancel()


async def _tree_changes_to_outline(
    tree_change_stream: TreeReceiveStream, outline_broadcast: BroadcastValue[Outline]
) -> None:
    async with tree_change_stream:
        async for tree in tree_change_stream:
            project_db = tree_to_project_database(tree)
            trail = project_db_to_trail(project_db)
            outline = Outline(trail=trail)
            outline_broadcast.set(outline)
