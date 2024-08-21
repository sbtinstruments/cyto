try:
    from ._frozen_model import FrozenModel
except ImportError as exc:
    from .._extra import ExtraImportError

    raise ExtraImportError.from_module_name(__name__) from exc

__all__ = ("FrozenModel",)
