try:
    from ._settings import cyto_defaults, register
except ImportError as exc:
    from .._extra import ExtraImportError

    raise ExtraImportError.from_module_name(__name__) from exc


__all__ = (
    "cyto_defaults",
    "register",
)
