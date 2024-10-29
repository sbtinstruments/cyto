from collections.abc import Callable
from pathlib import Path
from typing import Literal, TypeVar

from pydantic_settings import BaseSettings as PydanticBaseSettings
from pydantic_settings import CliSettingsSource, PydanticBaseSettingsSource
from pydantic_settings import SettingsConfigDict as PydanticSettingsConfigDict

from .sources.glob import GlobSource

T = TypeVar("T", bound=PydanticBaseSettings)


def cyto_defaults(
    *,
    name: str | None = None,
    cli_source: Literal["built-in", "disable"] | None = None,
    extra_sources: tuple[type[PydanticBaseSettingsSource], ...] | None = None,
) -> Callable[[type[T]], type[T]]:
    if cli_source is None:
        cli_source = "built-in"
    if extra_sources is None:
        extra_sources = ()

    def decorator(cls: type[T]) -> type[T]:
        nonlocal name
        if name is None:
            # E.g.: "FooBarSettings" -> "foobar"
            name = cls.__name__.removesuffix("Settings").lower()

        class _BaseSettings(cls):  # type: ignore[valid-type,misc]
            cls.model_config = PydanticSettingsConfigDict(
                # ## Priority
                #
                # > If you need to load multiple dotenv files, you can pass multiple
                # > file paths as a tuple or list. The files will be loaded in order,
                # > with each file overriding the previous one.
                #
                # From: https://docs.pydantic.dev/latest/concepts/pydantic_settings/#dotenv-env-support
                #
                #
                # ## Docker secret
                #
                # Pydantic supports Docker *secret*s out of the box. However,
                # Pydantic expects a secret *per field*. That's a lot of
                # individual secrets. We prefer to just provide everything in a
                # single *secret* akin to how an *env* file works. To do so, we
                # simply add `/run/secrets/{name}` to the `env_file` list (listing
                # it first to give it lowest priority).
                #
                env_file=(f"/run/secrets/{name}", ".env"),
                env_file_encoding="utf-8",
                env_prefix=f"{name}_",
                cli_prog_name=name,
            )

            @classmethod
            def settings_customise_sources(
                cls,
                settings_cls: type[PydanticBaseSettings],
                init_settings: PydanticBaseSettingsSource,
                env_settings: PydanticBaseSettingsSource,
                dotenv_settings: PydanticBaseSettingsSource,
                file_secret_settings: PydanticBaseSettingsSource,
            ) -> tuple[PydanticBaseSettingsSource, ...]:
                assert extra_sources is not None
                # Many false-positives because we use code in the comments below.
                # ruff: noqa: ERA001

                # Note that the pydantic_settings-provided default is:
                #
                #  1. init_settings
                #  2. env_settings
                #  3. dotenv_settings
                #  4. file_secret_settings
                #

                result: list[PydanticBaseSettingsSource] = [
                    # First (highest precedence), settings given via the constructor
                    # itself directly within Python. E.g.:
                    #
                    #     settings = Settings(debug=True, background=True)
                    #
                    init_settings,
                ]
                if cli_source == "built-in":
                    result.append(
                        # CLI settings (if you enable this extra). E.g.:
                        #
                        #     $ ./appster --debug --background
                        #
                        CliSettingsSource(
                            settings_cls, cli_parse_args=True, cli_exit_on_error=False
                        )
                    )
                result.extend(
                    [
                        # Settings from environment variables. E.g.:
                        #
                        #     $ APPSTER_DEBUG=y APPSTER_BACKGROUND=y ./appster
                        #
                        env_settings,
                        # Via ".env" files.
                        dotenv_settings,
                        # Settings from secret files. E.g., files in
                        #
                        #     /var/run/database_password
                        #     /var/run/backend_ip_address
                        #
                        file_secret_settings,
                        # Setting files from the current directory. E.g.:
                        #
                        #     ./dev-credentials.appster.toml
                        #     ./z10-relocate-db.appster.json
                        #     ./z99-disable-ssl.appster.toml
                        #
                        # Note that we apply multiple setting files in alphanumeric
                        # order.
                        GlobSource(settings_cls, Path("./"), f"*.{name}.*"),
                        # Setting files from the system's settings
                        # directory. E.g.:
                        #
                        #     /etc/appster/base-settings.toml
                        #     /etc/appster/z10-relocate-db.toml
                        #     /etc/appster/z99-disable-ssl.toml
                        #
                        # Note that we apply multiple setting files in alphanumeric
                        # order.
                        GlobSource(settings_cls, Path(f"/etc/{name}"), "*.*"),
                        # User-provided settings sources (if any)
                        *(source_cls(settings_cls) for source_cls in extra_sources),
                    ]
                )
                return tuple(result)

        # Similar to what functools.wraps does for a function.
        _BaseSettings.__module__ = cls.__module__
        _BaseSettings.__name__ = cls.__name__
        _BaseSettings.__qualname__ = cls.__qualname__
        _BaseSettings.__doc__ = cls.__doc__
        _BaseSettings.__annotations__ = cls.__annotations__
        _BaseSettings.__type_params__ = cls.__type_params__

        return _BaseSettings

    return decorator
