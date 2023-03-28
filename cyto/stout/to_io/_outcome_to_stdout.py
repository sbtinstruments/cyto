import logging
import sys

from .._outcome import OutcomeStream
from .._stout import OutcomeSwig

_LOGGER = logging.getLogger(__name__)


async def outcome_to_stdout(outcome_stream: OutcomeStream) -> None:
    async with outcome_stream as outcomes:
        async for outcome in outcomes:
            swig = OutcomeSwig(outcome=outcome)
            try:
                swig.write()
                sys.stdout.flush()
            except BrokenPipeError as exc:
                raise RuntimeError(
                    "Could not write swig to stdout since the latter closed"
                ) from exc
