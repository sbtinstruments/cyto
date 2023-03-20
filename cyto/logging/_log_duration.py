import inspect
import logging
from contextlib import contextmanager
from time import perf_counter
from typing import Callable, Iterator

_LOGGER = logging.getLogger(__name__)

TimeFunc = Callable[[], float]


@contextmanager
def log_duration(
    *,
    time_func: TimeFunc | None = None,
    logger: logging.Logger | None = None,
    log_level: int | None = None,
    log_message: str | None = None,
) -> Iterator[None]:
    """Time the duration of the wrapped code and log the result."""
    if time_func is None:
        time_func = perf_counter
    if logger is None:
        logger = _LOGGER
    if log_level is None:
        log_level = logging.DEBUG
    if log_message is None:
        log_message = _frames_to_log_message(inspect.stack(context=0))
    begin = perf_counter()
    try:
        yield
    except BaseException as exc:
        exc_name = type(exc).__name__
        log_message += f". Note that log_duration exited early due to {exc_name}."
        raise
    finally:
        end = perf_counter()
        elapsed = end - begin
        logger.log(log_level, log_message, elapsed)


def _frames_to_log_message(frames: list[inspect.FrameInfo]) -> str:
    try:
        # Note that:
        #
        #  * Frame 0: Is for `log_duration` itself
        #  * Frame 1: Is for `@contextmanager`
        #  * Frame 2: Is the actual "caller" (where the `with log_duration`
        #    statement is)
        #
        parent_frame = frames[2]
    except IndexError:
        return "Duration %.3f"
    else:
        func_name = parent_frame.function
        func_line = parent_frame.lineno
    return f"Code block (starting at line {func_line}) in {func_name} took %.3f seconds"
