from pathlib import Path
from typing import Callable, Type, TypeVar

from pydantic import BaseSettings

from ..settings import autofill as base_autofill

SettingsT = TypeVar("SettingsT", bound=BaseSettings)


def autofill() -> Callable[[Type[SettingsT]], Type[SettingsT]]:
    """Fill in the blanks based on setting files, env vars, etc."""
    # TODO: Figure out name dynamically
    return base_autofill("monty")


class Settings(BaseSettings):
    """Application base settings."""

    debug: bool = False
    foreground: bool = False
    data_directory: Path

    class Config:  # pylint: disable=too-few-public-methods
        allow_mutation = False
