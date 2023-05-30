import logging
from contextlib import contextmanager
from typing import Iterator

from ._log_message import frames_to_log_message

_LOGGER = logging.getLogger(__name__)


@contextmanager
def log_and_suppress(
    *exc_types: type[BaseException],
    logger: logging.Logger | None = None,
    log_level: int | None = None,
    log_message: str | None = None,
) -> Iterator[None]:
    """Log and suppress any exceptions of the given type(s)."""
    if logger is None:
        logger = _LOGGER
    if log_level is None:
        log_level = logging.ERROR
    if log_message is None:
        log_message = frames_to_log_message()
        log_message += " raised: %s"
    try:
        yield
    except exc_types as exc:
        logger.log(log_level, log_message, exc)
        logger.debug("Reason:", exc_info=exc)
        # We suppres the exception by not raising it again here.
