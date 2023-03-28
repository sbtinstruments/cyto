try:
    from ._outline_to_redis import outline_to_redis
except ImportError as exc:
    from ..._extra import ExtraImportError

    raise ExtraImportError.from_module_name(__name__) from exc
