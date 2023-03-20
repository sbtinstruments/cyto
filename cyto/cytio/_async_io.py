from io import TextIOBase
from typing import AsyncIterable

from anyio import to_thread


async def io_to_async_iterable(
    io: TextIOBase, *, line_limit: int
) -> AsyncIterable[str]:
    """Return async iterable of lines from the given IO stream.

    Does not take ownership of the `io`. Merely consumes items from `io`.
    It's up to the caller to close `io` as appropriate.
    """
    while line := await _readline(io, line_limit):
        yield line


# TODO: Replace `_readline` with `anyio.AsyncFile.readline` when the latter
# supports `line_limit`.
async def _readline(io: TextIOBase, line_limit: int) -> str:
    return await to_thread.run_sync(io.readline, line_limit)
