from pathlib import Path
from typing import ClassVar, TypeVar

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings

from ..settings import cyto_defaults

SettingsT = TypeVar("SettingsT", bound=BaseSettings)


@cyto_defaults(name="TODO")
class AppBaseSettings(BaseSettings):
    """Application base settings."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    debug: bool = Field(default=False, description="Enable debug checks.")
    background: bool = Field(
        default=True,
        description="Daemonize this process.",
    )

    # TODO: Work something out with these dynamic paths. See baxter for inspiration.
    # data_directory: Path = Field(
    #     description="Where this app stores its data.",
    # )
