from pathlib import Path
from typing import Callable, Iterable, Tuple, Type, TypeVar

from pydantic import BaseSettings
from pydantic.env_settings import SettingsSourceCallable

from ._cli import cli_settings
from ._sources import GlobSource

SettingsT = TypeVar("SettingsT", bound=BaseSettings)


def autofill(
    name: str,
    *,
    extra_sources: Iterable[SettingsSourceCallable] = tuple(),
) -> Callable[[Type[SettingsT]], Type[SettingsT]]:
    """Fill in the blanks based on setting files, env vars, etc."""

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
                    return (
                        init_settings,
                        cli_settings(name),
                        env_settings,
                        file_secret_settings,
                        GlobSource(Path("./"), f"*.{name}.toml"),
                        GlobSource(Path(f"/etc/{name}"), "*.toml"),
                        *extra_sources,
                    )

        # Mark the class so that we know that it is decorated
        _Wrapper.__autofill__ = True
        # Wraps
        _Wrapper.__name__ = base.__name__
        _Wrapper.__doc__ = base.__doc__
        return _Wrapper

    return _autofill
