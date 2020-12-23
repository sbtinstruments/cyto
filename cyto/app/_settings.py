from pathlib import Path
from typing import Any, Callable, Dict, Type, TypeVar

from pydantic import BaseSettings, Extra, Field
from pydantic.env_settings import SettingsSourceCallable

from ..settings import autofill as base_autofill

SettingsT = TypeVar("SettingsT", bound=BaseSettings)


def autofill(name: str) -> Callable[[Type[SettingsT]], Type[SettingsT]]:
    """Fill in the blanks based on setting files, env vars, etc."""
    extra_sources = (_app_computed_settings(name),)
    return base_autofill(name, extra_sources=extra_sources)


def _app_computed_settings(name: str) -> SettingsSourceCallable:
    def _source(_: BaseSettings) -> Dict[str, Any]:
        return {
            "data_directory": Path(f"/var/{name}"),
        }

    return _source


class Settings(BaseSettings):
    """Application base settings."""

    debug: bool = Field(False, description="Enable debug checks.")
    background: bool = Field(
        True,
        disable_name="foreground",
        description="Daemonize this process.",
    )
    data_directory: Path = Field(
        ...,
        description="Where this app stores its data.",
    )

    class Config:  # pylint: disable=too-few-public-methods
        allow_mutation = False
        extra = Extra.forbid
