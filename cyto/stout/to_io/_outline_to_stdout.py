import logging
import sys

from .._outline import OutlineStream
from .._stout import OutlineSwig

_LOGGER = logging.getLogger(__name__)


async def outline_to_stdout(outline_stream: OutlineStream) -> None:
    async with outline_stream as outlines:
        async for outline in outlines:
            swig = OutlineSwig(outline=outline)
            try:
                swig.write()
                sys.stdout.flush()
            except BrokenPipeError as exc:
                raise RuntimeError(
                    "Could not write swig to stdout since the latter closed"
                ) from exc
