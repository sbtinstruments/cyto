try:
    from ._settings import cyto_defaults as cyto_defaults
    from ._settings_var import SettingsVar as SettingsVar
except ImportError as exc:
    from .._extra import ExtraImportError

    raise ExtraImportError.from_module_name(__name__) from exc
