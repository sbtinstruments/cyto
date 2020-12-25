try:
    from ._autofill import autofill
except ImportError as exc:
    from .._extra import ExtraImportError

    raise ExtraImportError("settings") from exc
