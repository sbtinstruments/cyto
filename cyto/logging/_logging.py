import logging
import logging.handlers
import os
from collections.abc import Iterable
from typing import Literal


def initialize_logging(
    *,
    logger: logging.Logger | None = None,
    app_name: str | None = None,
    level: Literal["debug", "info", "warning", "error", "critical"] | None = None,
    handlers: Iterable[Literal["stderr", "syslog"]] | None = None,
) -> None:
    """Configure the global logging framework.

    Call this once during startup.

    TODO: Add config parameters to override the environment variables.
    """
    if logger is None:
        logger = logging.getLogger()

    # Level
    if level is None:
        level = "debug" if "DEBUG" in os.environ else "info"
    logger.setLevel(level.upper())  # type: ignore[union-attr]

    # Warnings
    logging.captureWarnings(capture=True)

    # Handler (where to send the log messages to)
    handlers_resolved: Iterable[str]
    if handlers is None:
        handler_name = os.environ.get("LOG_HANDLER", "stderr")
        handlers_resolved = (handler_name,)
    else:
        handlers_resolved = handlers
    for handler_name in handlers_resolved:
        match handler_name:
            case "stderr":
                _add_stderr_handler(logger)
            case "syslog":
                _add_syslog_handler(logger, app_name=app_name)
            case other:
                raise RuntimeError(f"Unknown '{other}' log handler")


def _add_stderr_handler(logger: logging.Logger) -> None:
    stderr_handler = (
        logging.StreamHandler()  # stderr is the default
    )  # Default stream is stderr, which we want
    stderr_handler.setLevel(logging.DEBUG)  # TODO: Can we leave it at NOTSET?
    formatter = logging.Formatter(
        "%(asctime)s - %(process)s - %(name)s - %(levelname)s - %(message)s"
    )
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)


def _add_syslog_handler(logger: logging.Logger, *, app_name: str | None = None) -> None:
    facility = logging.handlers.SysLogHandler.LOG_DAEMON
    syslog_handler = logging.handlers.SysLogHandler(
        address="/dev/log", facility=facility
    )
    syslog_handler.setLevel(logging.DEBUG)  # TODO: Can we leave it at NOTSET?
    # Optional: Use the RFC5424 format
    try:
        from .rfc5424 import RFC5424Formatter  # pylint: disable=import-outside-toplevel
    except ImportError:
        fmt = f"{app_name}" + "[{process}] [{name}] {message}"
        syslog_formatter = logging.Formatter(fmt=fmt, style="{")
        syslog_handler.setFormatter(syslog_formatter)
    else:
        syslog_handler.setFormatter(RFC5424Formatter(app_name=app_name))
    logger.addHandler(syslog_handler)
