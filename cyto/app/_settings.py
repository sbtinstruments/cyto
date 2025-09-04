from typing import ClassVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..settings import cyto_defaults


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
