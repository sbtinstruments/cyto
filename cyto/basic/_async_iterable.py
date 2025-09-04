"""Various ReactiveX-inspired functions."""

from collections.abc import AsyncIterable, AsyncIterator


class _Sentinel:
    pass


async def start_with[T](iterable: AsyncIterable[T], value: T) -> AsyncIterable[T]:
    """Return the given iterable but preceeded by the given value."""
    yield value
    async for datum in iterable:
        yield datum


async def distinct_until_changed[T](iterable: AsyncIterable[T]) -> AsyncIterator[T]:
    """Yield only whenever the data in the given iterable changes."""
    previous_value: T | _Sentinel = _Sentinel()
    async for value in iterable:
        if value == previous_value:
            continue
        previous_value = value
        yield value
