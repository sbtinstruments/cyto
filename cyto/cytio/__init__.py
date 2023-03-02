try:
    from ._cancel_on_signal import cancel_on_signal
    from ._scopes import wait_exactly, wait_if_faster, warn_after
except ImportError as exc:
    from .._extra import ExtraImportError

    raise ExtraImportError.from_module_name(__name__) from exc
