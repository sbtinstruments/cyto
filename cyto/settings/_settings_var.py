import contextvars
from collections.abc import Callable
from typing import Any, Literal

GetMode = Literal["reset-if-none", "force-reset"]

type SettingsFactory[T] = Callable[[], T]


class SettingsVar[T]:
    def __init__(
        self,
        *,
        name: str,
        default_factory: SettingsFactory[T],
    ) -> None:
        self._settings = contextvars.ContextVar[T](name)
        self._default_factory = default_factory

    def get(self, *, mode: GetMode | None = None) -> T:
        if mode is None:
            mode = "reset-if-none"

        match mode:
            case "force-reset":
                self.reset()
            case "reset-if-none":
                try:
                    return self._settings.get()
                except LookupError:
                    self.reset()
            case _:
                raise ValueError(f"Unknown mode '{mode}'")
        return self._settings.get()

    def reset(self, *args: Any, **kwargs: Any) -> None:
        self._settings.set(self._default_factory(*args, **kwargs))
