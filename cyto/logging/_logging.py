import logging
import logging.handlers
import os


def initialize_logging(app_name: str | None = None) -> None:
    """Configure the global logging framework.

    Call this once during startup.

    TODO: Add config parameters to override the environment variables.
    """
    root = logging.getLogger()

    # Level
    if "DEBUG" in os.environ:
        level = logging.DEBUG
    else:
        level = logging.INFO
    root.setLevel(level)

    # Warnings
    logging.captureWarnings(True)

    # Handler
    handler_name = os.environ.get("LOG_HANDLER", "stderr")
    match handler_name:
        case "stderr":
            _add_stderr_handler(root)
        case "syslog":
            _add_syslog_handler(root, app_name=app_name)
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
        pass
    else:
        syslog_handler.setFormatter(RFC5424Formatter(app_name=app_name))
    logger.addHandler(syslog_handler)
