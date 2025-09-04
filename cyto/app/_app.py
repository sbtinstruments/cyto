from __future__ import annotations

import inspect
import logging
from contextlib import AbstractContextManager, ExitStack
from types import TracebackType
from typing import Any, Self, cast

from anyio import run

from ..basic import get_app_name
from ._inject import Func, inject
from ._settings import AppBaseSettings

_LOGGER = logging.getLogger(__name__)


class App(AbstractContextManager["App"]):
    """Useful defaults for applications."""

    def __init__(self, name: str, settings: AppBaseSettings) -> None:
        self._name = name
        self._settings = settings
        self._stack = ExitStack()

    @property
    def name(self) -> str:
        """Application name."""
        return self._name

    @property
    def settings(self) -> AppBaseSettings:
        """Application settings."""
        return self._settings

    @classmethod
    def launch[ReturnT](
        cls,
        func: Func[ReturnT],
        *,
        name: str | None = None,
        settings_class: type[AppBaseSettings] | None = None,
    ) -> ReturnT:
        """Create app instance and run the given coroutine function."""
        # Set defaults for optional arguments
        if name is None:
            name = get_app_name(func)
        if settings_class is None:
            settings_class = get_settings_class(func)
        # Create settings instance
        settings: AppBaseSettings = settings_class()
        # Create and run app instance
        with cls(name, settings) as app:
            return app.run(func)

    def run[ReturnT](self, func: Func[ReturnT]) -> ReturnT:
        """Execute the coroutine function and return the result."""
        # Inject dependencies (e.g., a task group, settings, stack, etc.)
        injected_func = inject(extra_factory=self._factory)(func)
        # Run until the task completes (or the process receives a signal)
        return run(injected_func)

    async def _factory(self, annotation: type[Any]) -> Any:
        """Return instance based on the given annotation.

        We use this function for dependency injection.
        """
        if issubclass(annotation, App):
            return self
        if issubclass(annotation, AppBaseSettings):
            return self._settings
        raise ValueError

    def __enter__(self) -> Self:
        try:
            self._stack.__enter__()
        except Exception as error:
            _LOGGER.error("Could not start due to error:", exc_info=error)
            raise
        _LOGGER.info("Started")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        suppress_exc = self._stack.__exit__(exc_type, exc_value, traceback)
        # Log exit
        if exc_value is not None:
            # We exit due to a problem
            _LOGGER.error("Stopped due to error:", exc_info=exc_value)
        else:
            _LOGGER.info("Stopped")
        return suppress_exc


def get_settings_class[ReturnT](func: Func[ReturnT]) -> type[AppBaseSettings]:
    """Try to get the settings class from the function signature."""
    spec = inspect.getfullargspec(func)
    for arg_name in spec.args:
        try:
            annotation = spec.annotations[arg_name]
        except KeyError:
            continue
        if issubclass(annotation, AppBaseSettings):
            # Strangely, mypy can't infer that `annotation` has the right
            # type from the `issubclass` call. We explicitly cast as a
            # work-around to this.
            return cast(type[AppBaseSettings], annotation)
    # Default to the base settings class
    return AppBaseSettings
