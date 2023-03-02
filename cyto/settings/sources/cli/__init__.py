try:
    from ._cli import CliExtras, cli_settings_source
except ImportError as exc:
    from ...._extra import ExtraImportError

    raise ExtraImportError.from_module_name(__name__) from exc
