import logging
import sys

from .._outcome import OutcomeStream
from .._outline import OutlineStream
from .._stout import OutcomeSwig, OutlineSwig

_LOGGER = logging.getLogger(__name__)


async def outcome_to_stdout(outcome_stream: OutcomeStream) -> None:
    async with outcome_stream as outcomes:
        async for outcome in outcomes:
            swig = OutcomeSwig(outcome=outcome)
            _write_and_flush(swig)


async def outline_to_stdout(outline_stream: OutlineStream) -> None:
    async with outline_stream as outlines:
        async for outline in outlines:
            swig = OutlineSwig(outline=outline)
            _write_and_flush(swig)


def _write_and_flush(swig: OutcomeSwig | OutlineSwig) -> None:
    try:
        swig.write()
        sys.stdout.flush()
    except BrokenPipeError as exc:
        raise RuntimeError(
            "Could not write swig to stdout since the latter closed"
        ) from exc
