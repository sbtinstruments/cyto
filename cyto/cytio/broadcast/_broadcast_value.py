from __future__ import annotations

from dataclasses import dataclass
from types import TracebackType
from typing import Generic, Literal, TypeVar, Union, cast

from anyio import BrokenResourceError, WouldBlock, create_memory_object_stream
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

Seed = Literal["latest-value", "first-value", "nothing"]


T = TypeVar("T")
StreamPair = tuple[MemoryObjectSendStream[T], MemoryObjectReceiveStream[T]]


class NoValue:
    pass


# TODO: Figure out why mypy can't use the pipe syntax for unions in this case.
MaybeValue = Union[T, type[NoValue]]  # noqa: UP007


@dataclass(frozen=True)
class Subscription(Generic[T]):
    send_stream: MemoryObjectSendStream[T]
    receive_stream: MemoryObjectReceiveStream[T]


class BroadcastValue(Generic[T]):
    """Like a "behaviour subject" from reactive functional programming.

    Use this when you want a stream of something but you're only interested in
    the latest value.

    Inspiration:
     * https://github.com/python-trio/trio/issues/987
     * https://reactivex.io/documentation/subject.html
    """

    def __init__(self, value: MaybeValue[T] = NoValue) -> None:
        # We use a sentinel instead of None since the latter is a valid value
        self._first_value: MaybeValue[T] = value
        self._latest_value: MaybeValue[T] = value
        self._subscriptions: set[Subscription[T]] = set()
        self._closed = False

    @property
    def first_value(self) -> MaybeValue[T]:
        return self._first_value

    @property
    def latest_value(self) -> MaybeValue[T]:
        return self._latest_value

    def subscribe(self, *, seed: Seed | None = None) -> MemoryObjectReceiveStream[T]:
        if self._closed:
            raise RuntimeError("Can't subscribe to closed broadcast")

        if seed is None:
            seed = "latest-value"
        stream_pair: StreamPair[T] = create_memory_object_stream(1)
        sub = Subscription(*stream_pair)
        self._subscriptions.add(sub)
        # Seed stream
        if seed == "latest-value":
            if self._latest_value is not NoValue:
                sub.send_stream.send_nowait(cast(T, self._latest_value))
        elif seed == "first-value" and self._first_value is not NoValue:
            sub.send_stream.send_nowait(cast(T, self._first_value))
        return sub.receive_stream

    def publish(self, value: T) -> None:
        if self._closed:
            raise RuntimeError("Can't publish value of closed broadcast")

        if self._first_value is NoValue:
            self._first_value = value

        closed_subs: set[Subscription[T]] = set()
        for sub in self._subscriptions:
            try:
                sub.send_stream.send_nowait(value)
            except WouldBlock:  # Stream buffer is full
                # Replace the existing item
                sub.receive_stream.receive_nowait()
                sub.send_stream.send_nowait(value)
            except BrokenResourceError:  # Receiver closed the stream
                closed_subs.add(sub)
        for sub in closed_subs:
            sub.send_stream.close()  # Just for good measure. It's not really necessary.
            self._subscriptions.remove(sub)

        self._latest_value = value

    def close(self) -> None:
        if self._closed:
            return
        for sub in self._subscriptions:
            sub.send_stream.close()

    def __enter__(self) -> BroadcastValue[T]:
        return self

    def __exit__(  # type: ignore[return]
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        self.close()
