import logging
from io import TextIOBase
from typing import AsyncIterable

from anyio.abc import ByteReceiveStream
from anyio.streams.text import TextReceiveStream
from pydantic import parse_raw_as

from cyto.cytio import io_to_async_iterable

from .._stout import Stout, Swig

_LOGGER = logging.getLogger()  # Root logger


RawInput = TextIOBase | AsyncIterable[str] | TextReceiveStream | ByteReceiveStream


async def raw_input_to_stout(
    raw_input: RawInput,
    line_limit: int | None = None,
    ignore_empty_lines: bool | None = None,
) -> Stout:
    """Convert raw input (e.g., stream I/O) to STOUT (stream of swigs)."""
    # Default arguments
    if line_limit is None:
        # Default limit is 1 MiB. It's important to have a limit to avoid
        # out-of-memory errors. E.g., if `sys.stdin` is an infinite stream
        # (as produced by `cat /dev/zero` or the like).
        line_limit = 1024**2  # 1 MiB
    if ignore_empty_lines is None:
        ignore_empty_lines = True

    # Transform input
    match raw_input:
        case TextIOBase():
            lines = io_to_async_iterable(raw_input, line_limit=line_limit)
        case ByteReceiveStream():
            lines = TextReceiveStream(raw_input, "utf8")
        case _:
            lines = raw_input

    # Note that `line` includes the separator ("\n") at the end
    async for line in lines:
        if ignore_empty_lines and (not line or line.isspace()):
            continue
        if len(line) == line_limit:
            _LOGGER.warning(
                (
                    "IO stream reached the line limit (%d bytes). This will most likely"
                    " result in a parse error. Either reduce the size of the STOUT"
                    " swigs or increase the line limit"
                ),
                line_limit,
            )
        try:
            # mypy see `Swig` as "<typing special form>", which mypy apparently doesn't
            # think fits with `parse_raw_as`. We ignore the error for now.
            yield parse_raw_as(Swig, line)  # type: ignore[arg-type]
        except ValueError as exc:
            _log_start_of_string_as_binary(line)
            raise RuntimeError(
                f"Could not parse line from IO stream into STOUT swig: {exc}"
            ) from exc


def _log_start_of_string_as_binary(line: str) -> None:
    char_count = 20
    first = line[:char_count]
    raw = first.encode("utf8")
    _LOGGER.info("The first %d characters of the line are: %s", char_count, raw)
