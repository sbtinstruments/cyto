try:
    from ._cli import CliExtras, cli_settings_source
except ImportError as exc:
    from ...._extra import ExtraImportError

    raise ExtraImportError(__name__) from exc
