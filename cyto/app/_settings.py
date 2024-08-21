from typing import ClassVar, TypeVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..settings import cyto_defaults

SettingsT = TypeVar("SettingsT", bound=BaseSettings)


@cyto_defaults(name="TODO")
class AppBaseSettings(BaseSettings):
    """Application base settings."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        frozen=True,
        extra="forbid",
    )

    debug: bool = Field(default=False, description="Enable debug checks.")
    background: bool = Field(
        default=True,
        description="Daemonize this process.",
    )
