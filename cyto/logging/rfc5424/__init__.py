try:
    from ._rfc5424 import RFC5424Formatter
except ImportError as exc:
    from ..._extra import ExtraImportError

    raise ExtraImportError.from_module_name(__name__) from exc
