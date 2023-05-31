from __future__ import annotations

import logging
from collections.abc import Iterator, MutableMapping
from contextlib import contextmanager
from typing import TypeVar

from anyio.streams.memory import MemoryObjectReceiveStream

from .._broadcast_value import BroadcastValue

_LOGGER = logging.getLogger(__name__)

KT = TypeVar("KT")
VT = TypeVar("VT")


class BroadcastMap(MutableMapping[KT, VT]):
    def __init__(self) -> None:
        self._data: dict[KT, VT] = {}
        self._broadcast = BroadcastValue(self)

    def subscribe(self) -> MemoryObjectReceiveStream[BroadcastMap[KT, VT]]:
        """Subscribe to this broadcast.

        Remember to enter the returned context manager before you iterate it! E.g.:

        ```python
        async with my_broadcast.subscribe() as stream:
            async for datum in stream:
                ...
        ```
        """
        return self._broadcast.subscribe()

    def __getitem__(self, key: KT) -> VT:
        # In principle, we should broadcast here as well because `self._data`
        # is a `defaultdict` that may mutate on access.
        return self._data[key]

    def __setitem__(self, key: KT, value: VT) -> None:
        self._data[key] = value
        self._broadcast.publish(self)

    def __delitem__(self, key: KT) -> None:
        del self._data[key]
        self._broadcast.publish(self)

    def __iter__(self) -> Iterator[KT]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    @contextmanager
    def mutate(self) -> Iterator[dict[KT, VT]]:
        try:
            yield self._data
        finally:
            self._broadcast.publish(self)
