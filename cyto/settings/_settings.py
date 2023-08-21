from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel, BaseSettings, Field, create_model

_SETTINGS: dict[str, type[BaseModel]] = {}


T = TypeVar("T", bound=BaseModel)


def register(
    name: str, *, override: bool | None = None
) -> Callable[[type[T]], type[T]]:
    """Register application-wide settings class.

    Raises `RuntimeError` if there already is a settings class for the given name
    *unless* `override=True`.
    Analogously, raises `RuntimeError` if there is no existing settings class for
    the given name *and* `override=True`.
    In other words, we are very strict about the use of the `override` paramater.
    This is an effort to avoid common pitfalls such as accidental overrides or
    non-effectual overrides.
    """

    if override is None:
        override = False

    def _register(settings: type[T]) -> type[T]:
        if name in _SETTINGS:
            if not override:
                raise RuntimeError(
                    "There is already a settings class registered under the "
                    f"'{name}' name. Use 'override=True' to suppress this error."
                )
        elif override:
            raise RuntimeError(
                "There is no existing settings class registered under the "
                f"'{name}' name. In this case, it's an error to use 'override=True' "
                "since there is nothing to override."
            )
        _SETTINGS[name] = settings
        return settings

    return _register


def get_base_settings_class() -> type[BaseSettings]:
    """Return class for the application-wide settings."""
    field_definitions: dict[str, Any] = {
        name: (cls, Field(default_factory=cls)) for name, cls in _SETTINGS.items()
    }
    return create_model("Settings", __base__=BaseSettings, **field_definitions)
