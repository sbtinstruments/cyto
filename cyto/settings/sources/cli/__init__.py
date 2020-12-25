try:
    from ._cli import cli_settings
except ImportError as exc:
    from ...._extra import ExtraImportError

    raise ExtraImportError("settings.sources.cli") from exc
