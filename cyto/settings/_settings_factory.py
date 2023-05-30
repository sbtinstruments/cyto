from typing import Callable, Iterable, TypeVar

from pydantic.env_settings import SettingsSourceCallable

from ..factory import CanNotProduce, ProductSpec
from ._autofill import autofill
from ._settings import _SETTINGS, get_base_settings_class

T = TypeVar("T")


def settings_factory(
    *, extra_sources: Iterable[SettingsSourceCallable] = tuple()
) -> Callable[[ProductSpec[T]], T]:
    def _settings_factory(spec: ProductSpec[T]) -> T:
        if spec.annotation not in _SETTINGS.values():
            raise CanNotProduce
        cls = get_base_settings_class()
        # TODO: Use app_name instead of mytest1
        # TODO: LRU cache for both `auto_cls` and `all_settings`
        auto_cls = autofill("mytest1", extra_sources=extra_sources)(cls)
        all_settings = auto_cls()

        for _, setting in all_settings:
            if isinstance(setting, spec.annotation):
                return setting
        raise CanNotProduce

    return _settings_factory
