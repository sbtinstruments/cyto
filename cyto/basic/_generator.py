from typing import AsyncIterable, AsyncIterator, TypeVar, Union

T = TypeVar("T")


class _Sentinel:  # pylint: disable=too-few-public-methods
    pass


async def distinct_until_changed(iterable: AsyncIterable[T]) -> AsyncIterator[T]:
    previous_value: Union[T, _Sentinel] = _Sentinel()
    async for value in iterable:
        if value == previous_value:
            continue
        previous_value = value
        yield value
