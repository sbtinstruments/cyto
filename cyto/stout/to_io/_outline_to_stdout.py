import logging
import sys

from .._outline import OutlineStream
from .._stout import OutlineSwig

_LOGGER = logging.getLogger(__name__)


async def outline_to_stdout(outline_stream: OutlineStream) -> None:
    async with outline_stream as outlines:
        async for outline in outlines:
            # summary = OutlineSummary.from_outline(outline)
            swig = OutlineSwig(outline=outline)
            try:
                swig.write()
                sys.stdout.flush()
            except TypeError as exc:
                _LOGGER.debug(f"{swig=}")
                _LOGGER.debug("TYPE ERROR:", exc_info=exc)
                raise
            except BrokenPipeError as exc:
                raise RuntimeError(
                    "Could not write swig to stdout since the latter closed"
                ) from exc
