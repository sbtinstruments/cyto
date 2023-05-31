import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from time import perf_counter

from ._log_message import frames_to_log_message

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
        log_message = frames_to_log_message()
        if log_message:
            log_message += " took %.3f seconds"
        else:
            log_message += "Duration %.3f"
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
