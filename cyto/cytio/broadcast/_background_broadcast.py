from __future__ import annotations

import abc
import logging
from contextlib import AsyncExitStack
from typing import Any, Generic, TypeVar

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream

from ...basic import AsyncContextStack
from ._broadcast_value import BroadcastValue, MaybeValue, NoValue, Seed

_LOGGER = logging.getLogger(__name__)


MessageMap = dict[Any, Any]
T = TypeVar("T")


class BackgroundBroadcast(AsyncContextStack, Generic[T]):
    """Continuous broadcast emitted by a background task."""

    def __init__(self, value: MaybeValue[T] = NoValue) -> None:
        super().__init__()
        self._tg = anyio.create_task_group()
        self._broadcast: BroadcastValue[T] = BroadcastValue(value)

    @property
    def first_value(self) -> MaybeValue[T]:
        """Return the first value sent via this broadcast (if any)."""
        return self._broadcast.first_value

    @property
    def latest_value(self) -> MaybeValue[T]:
        """Return the latest value sent via this broadcast (if any)."""
        return self._broadcast.latest_value

    def subscribe(self, *, seed: Seed | None = None) -> MemoryObjectReceiveStream[T]:
        """Subscribe to this broadcast.

        Remember to enter the returned context manager before you iterate it! E.g.:

        ```python
        async with my_broadcast.subscribe() as stream:
            async for datum in stream:
                ...
        ```
        """
        return self._broadcast.subscribe(seed=seed)

    @abc.abstractmethod
    async def _maintain_broadcast(self) -> None:
        """Implement an endless loop that keeps the broadcast alive.

        Overrride this function in your child class. Use `self._broadcast.set` to
        send out messages to all subscribers.
        You may use `self._tg.start_soon` to start background tasks.
        """

    async def _aenter_stack(self, stack: AsyncExitStack) -> None:
        stack.enter_context(self._broadcast)
        await stack.enter_async_context(self._tg)
        stack.callback(self._tg.cancel_scope.cancel)
        self._tg.start_soon(self._maintain_broadcast)
