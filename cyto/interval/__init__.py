try:
    from ._interval import (
        FloatInterval,
        FloatIntervalAdapter,
        IntInterval,
        IntIntervalAdapter,
        TimeInterval,
        TimeIntervalAdapter,
    )
except ImportError as exc:
    from .._extra import ExtraImportError

    raise ExtraImportError.from_module_name(__name__) from exc


__all__ = (
    "FloatInterval",
    "FloatIntervalAdapter",
    "IntInterval",
    "IntIntervalAdapter",
    "TimeInterval",
    "TimeIntervalAdapter",
)
