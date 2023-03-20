try:
    from ._interval import Interval
except ImportError as exc:
    from .._extra import ExtraImportError

    raise ExtraImportError.from_module_name(__name__) from exc
