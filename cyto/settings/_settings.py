from typing import Callable, TypeVar

from pydantic import BaseModel, BaseSettings, Field, create_model

_SETTINGS: dict[str, type[BaseModel]] = {}


T = TypeVar("T", bound=BaseModel)


def register(name: str) -> Callable[[type[T]], type[T]]:
    def _register(settings: type[T]) -> type[T]:
        _SETTINGS[name] = settings
        return settings

    return _register


def get_base_settings_class() -> type[BaseSettings]:
    field_definitions = {
        name: (cls, Field(default_factory=cls)) for name, cls in _SETTINGS.items()
    }
    return create_model("Settings", __base__=BaseSettings, **field_definitions)
