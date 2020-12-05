from pathlib import Path
from typing import Callable, Tuple, Type, TypeVar

from pydantic import BaseSettings
from pydantic.env_settings import SettingsSourceCallable

from ._sources import GlobSource

SettingsT = TypeVar("SettingsT", bound=BaseSettings)


def autofill(name: str) -> Callable[[Type[SettingsT]], Type[SettingsT]]:
    """Fill in the blanks based on setting files, env vars, etc."""

    def _autofill(base: Type[SettingsT]) -> Type[SettingsT]:
        # Early out if the class already has the decoration
        if hasattr(base, "__autofill__"):
            return base

        extras = (
            GlobSource(Path("./"), f"*.{name}.toml"),
            GlobSource(Path(f"/etc/{name}"), "*.toml"),
        )

        class _Wrapper(base):  # type: ignore[valid-type, misc] # pylint: disable=too-few-public-methods
            data_directory: Path = Path(f"/var/{name}")

            class Config:  # pylint: disable=missing-docstring,too-few-public-methods
                env_prefix = f"{name}_"

                @classmethod
                def customise_sources(
                    cls,
                    init_settings: SettingsSourceCallable,
                    env_settings: SettingsSourceCallable,
                    file_secret_settings: SettingsSourceCallable,
                ) -> Tuple[SettingsSourceCallable, ...]:
                    return init_settings, env_settings, file_secret_settings, *extras

        # Mark the class so that we know that it is decorated
        _Wrapper.__autofill__ = True
        # Wraps
        _Wrapper.__name__ = base.__name__
        _Wrapper.__doc__ = base.__doc__
        return _Wrapper

    return _autofill
