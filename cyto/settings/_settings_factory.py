from collections.abc import Callable, Iterable
from typing import TypeVar

from pydantic.env_settings import SettingsSourceCallable

from ..factory import CanNotProduce, ProductSpec
from ._autofill import autofill
from ._settings import _SETTINGS, get_base_settings_class

T = TypeVar("T")


def settings_factory(
    *, app_name: str, extra_sources: Iterable[SettingsSourceCallable] = ()
) -> Callable[[ProductSpec[T]], T]:
    def _settings_factory(spec: ProductSpec[T]) -> T:
        if spec.annotation not in _SETTINGS.values():
            raise CanNotProduce
        cls = get_base_settings_class()
        # TODO: LRU cache for both `auto_cls` and `all_settings`
        auto_cls = autofill(app_name, extra_sources=extra_sources)(cls)
        all_settings = auto_cls()

        for _, setting in all_settings:
            if isinstance(setting, spec.annotation):
                return setting  # type: ignore[no-any-return]
        raise CanNotProduce

    return _settings_factory
