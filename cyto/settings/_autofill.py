from json import loads as json_loads
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional, Tuple, Type, TypeVar

from pydantic import BaseSettings
from pydantic.env_settings import SettingsSourceCallable

from .sources.glob import GlobSource, Loader

toml_loads: Optional[Loader]
try:
    from toml import loads as toml_loads
except ImportError:
    toml_loads = None

cli_settings_source: Optional[Callable[..., SettingsSourceCallable]]
try:
    from .sources.cli import cli_settings_source
except ImportError:
    cli_settings_source = None

SettingsT = TypeVar("SettingsT", bound=BaseSettings)


def autofill(
    name: str,
    *,
    extra_sources: Iterable[SettingsSourceCallable] = tuple(),
    cli_settings: Optional[Dict[str, Any]] = None,
) -> Callable[[Type[SettingsT]], Type[SettingsT]]:
    """Fill in the blanks based on setting files, env vars, etc."""
    if cli_settings is None:
        cli_settings = {}

    def _autofill(base: Type[SettingsT]) -> Type[SettingsT]:
        # Early out if the class already has this decoration
        if hasattr(base, "__autofill__"):
            return base

        class _Wrapper(base):  # type: ignore[valid-type, misc] # pylint: disable=too-few-public-methods
            class Config:  # pylint: disable=missing-docstring,too-few-public-methods
                env_prefix = f"{name}_"

                @classmethod
                def customise_sources(
                    cls,
                    init_settings: SettingsSourceCallable,
                    env_settings: SettingsSourceCallable,
                    file_secret_settings: SettingsSourceCallable,
                ) -> Tuple[SettingsSourceCallable, ...]:
                    """Apply setting sources with custom precedence."""
                    sources = [
                        # First (highest precedence), settings given via the constructor
                        # itself directly within Python. E.g.:
                        #   settings = Settings(debug=True, background=True)
                        init_settings
                    ]
                    if cli_settings_source is not None:
                        assert cli_settings is not None
                        # Second, CLI settings (if you enable this extra). E.g.:
                        #   $ ./appster --debug --background
                        sources.append(cli_settings_source(name, **cli_settings))
                    sources += [
                        # Third, settings from environment variables. E.g.:
                        #   $ APPSTER_DEBUG=y APPSTER_BACKGROUND=y ./appster
                        env_settings,
                        # Fourth, settings from secret files. E.g., files in
                        #   /var/run/database_password
                        #   /var/run/backend_ip_address
                        file_secret_settings,
                    ]
                    if toml_loads is not None:
                        sources += [
                            # Fifth, setting files from the current directory. E.g.:
                            #   ./dev-credentials.appster.toml
                            #   ./z10-relocate-db.appster.toml
                            #   ./z99-disable-ssl.appster.toml
                            # Note that we apply multiple setting files in alphanumeric
                            # order.
                            # Note that TOML files have higher precedence than
                            # JSON files. We may change this in the future. Don't rely
                            # on this behaviour
                            GlobSource(Path("./"), f"*.{name}.toml", toml_loads),
                            GlobSource(Path("./"), f"*.{name}.json", json_loads),
                            # Sixth, setting files from the system's settings
                            # directory. E.g.:
                            #   /etc/appster/base-settings.toml
                            #   /etc/appster/z10-relocate-db.toml
                            #   /etc/appster/z99-disable-ssl.toml
                            # Note that we apply multiple setting files in alphanumeric
                            # order.
                            # Note that TOML files have higher precedence than
                            # JSON files. We may change this in the future. Don't rely
                            # on this behaviour
                            GlobSource(Path(f"/etc/{name}"), "*.toml", toml_loads),
                            GlobSource(Path(f"/etc/{name}"), "*.json", json_loads),
                        ]
                    # Seventh (lowest precedence), you can specify additional setting
                    # sources.
                    sources += extra_sources
                    return tuple(sources)

        # Mark the class so that we know that it is decorated
        _Wrapper.__autofill__ = True
        # Wraps
        _Wrapper.__name__ = base.__name__
        _Wrapper.__doc__ = base.__doc__
        return _Wrapper

    return _autofill
