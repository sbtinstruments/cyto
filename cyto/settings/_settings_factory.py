from collections.abc import Callable, Iterable
from functools import cache
from typing import TypeVar

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from ..factory import CanNotProduce, ProductSpec
from ._settings import get_base_settings_class

T = TypeVar("T")


def settings_factory(
    *, app_name: str, extra_sources: Iterable[PydanticBaseSettingsSource] = ()
) -> Callable[[ProductSpec[T]], T]:
    frozen_extra_sources = tuple(extra_sources)
    all_settings = _get_all_settings(
        app_name=app_name, extra_sources=frozen_extra_sources
    )

    def _settings_factory(spec: ProductSpec[T]) -> T:
        # if spec.annotation not in _SETTINGS.values():
        #    raise CanNotProduce

        # TODO: Improve on this worst-case runtime of `O(n)`. For now,
        # there are very few settings (`n` is small), so it's okay.
        for _, setting in all_settings:
            if isinstance(setting, spec.annotation):
                return setting  # type: ignore[no-any-return]
        raise CanNotProduce

    return _settings_factory


@cache
def _get_all_settings(
    *, app_name: str, extra_sources: tuple[PydanticBaseSettingsSource, ...] = ()
) -> BaseSettings:
    auto_cls = _get_auto_cls(app_name=app_name, extra_sources=extra_sources)
    return auto_cls()


@cache
def _get_auto_cls(
    *, _app_name: str, _extra_sources: tuple[PydanticBaseSettingsSource, ...] = ()
) -> type[BaseSettings]:
    return get_base_settings_class()
