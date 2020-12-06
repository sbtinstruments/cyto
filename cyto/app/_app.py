from __future__ import annotations

import logging
from contextlib import ExitStack
from types import TracebackType
from typing import Any, ContextManager, Optional, Type, TypeVar

from anyio import run

from ._inject import Func, inject
from ._settings import Settings, autofill

_LOGGER = logging.getLogger(__name__)


ReturnT = TypeVar("ReturnT")


class App(ContextManager["App"]):
    """Useful defaults for applications."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._stack = ExitStack()

    @property
    def settings(self) -> Settings:
        """Application settings."""
        return self._settings

    @classmethod
    def launch(
        cls,
        func: Func[ReturnT],
        settings_class: Optional[Type[Settings]] = None,
    ) -> ReturnT:
        """Create app instance and run the given coroutine function."""
        # Set defaults for optional arguments
        if settings_class is None:
            settings_class = Settings
        # Automatically fill in missing settings (e.g., from settings files)
        settings_class = autofill()(settings_class)
        # Create settings instance
        settings: Settings = settings_class()
        # Create and run app instance
        with cls(settings) as app:
            return app.run(func)

    def run(self, func: Func[ReturnT]) -> ReturnT:
        """Execute the coroutine function and return the result."""
        # Inject dependencies (e.g., a task group, settings, stack, etc.)
        injected_func = inject(extra_factory=self._factory)(func)
        # Run until the task completes (or the process receives a signal)
        return run(injected_func)

    async def _factory(self, annotation: Type[Any]) -> Any:
        """Return instance based on the given annotation.

        We use this function for dependency injection.
        """
        if issubclass(annotation, Settings):
            return self._settings
        raise ValueError

    def __enter__(self) -> App:
        try:
            self._stack.__enter__()
        except Exception as error:
            _LOGGER.error("Could not start due to error:", exc_info=error)
            raise
        _LOGGER.info("Started")
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self._stack.__exit__(exc_type, exc_value, traceback)
        # Log exit
        if exc_value is not None:
            # We exit due to a problem
            _LOGGER.error("Stopped due to error:", exc_info=exc_value)
        else:
            _LOGGER.info("Stopped")
