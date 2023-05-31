from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterator, MutableMapping
from contextlib import contextmanager
from typing import Any

from anyio.streams.memory import MemoryObjectReceiveStream
from pydantic import validate_arguments

from ...cytio.broadcast import BroadcastValue
from ...stout import Message, ResultMap

_LOGGER = logging.getLogger(__name__)


OutcomeLayerMap = MutableMapping[str, ResultMap]


class LayerMap(OutcomeLayerMap):
    def __init__(self) -> None:
        self._data: defaultdict[str, ResultMap] = defaultdict(ResultMap)
        self._broadcast = BroadcastValue(self)

    def subscribe(self) -> MemoryObjectReceiveStream[LayerMap]:
        """Subscribe to this broadcast.

        Remember to enter the returned context manager before you iterate it! E.g.:

        ```python
        async with my_broadcast.subscribe() as stream:
            async for datum in stream:
                ...
        ```
        """
        return self._broadcast.subscribe()

    def __getitem__(self, layer_name: str) -> ResultMap:
        # In principle, we should broadcast here as well because `self._data`
        # is a `defaultdict` that may mutate on access.
        return self._data[layer_name]

    @validate_arguments
    def __setitem__(self, layer_name: str, value: ResultMap) -> None:
        self._data[layer_name] = value
        self._broadcast.publish(self)

    def __delitem__(self, layer_name: str) -> None:
        del self._data[layer_name]
        self._broadcast.publish(self)

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    @contextmanager
    def mutate(self, layer_name: str) -> Iterator[dict[str, Any]]:
        mutable_layer = self[layer_name].dict()
        try:
            yield mutable_layer
        finally:
            self[layer_name] = ResultMap.parse_obj(mutable_layer)


class MessageMap(MutableMapping[str, Message]):
    def __init__(self) -> None:
        self._data: dict[str, Message] = {}
        self._broadcast = BroadcastValue(self)

    def subscribe(self) -> MemoryObjectReceiveStream[MessageMap]:
        """Subscribe to this broadcast.

        Remember to enter the returned context manager before you iterate it! E.g.:

        ```python
        async with my_broadcast.subscribe() as stream:
            async for datum in stream:
                ...
        ```
        """
        return self._broadcast.subscribe()

    def __getitem__(self, code: str) -> Message:
        return self._data[code]

    def __setitem__(self, code: str, value: Message) -> None:
        self._data[code] = value
        self._broadcast.publish(self)

    def __delitem__(self, code: str) -> None:
        del self._data[code]
        self._broadcast.publish(self)

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)
