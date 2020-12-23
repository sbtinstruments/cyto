from __future__ import annotations

import inspect
import logging
from contextlib import ExitStack
from pathlib import Path
from types import TracebackType
from typing import Any, ContextManager, Optional, Type, TypeVar, cast

from anyio import run

from ._inject import Func, inject
from ._settings import Settings, autofill

_LOGGER = logging.getLogger(__name__)


ReturnT = TypeVar("ReturnT")


class App(ContextManager["App"]):
    """Useful defaults for applications."""

    def __init__(self, name: str, settings: Settings) -> None:
        self._name = name
        self._settings = settings
        self._stack = ExitStack()

    @property
    def name(self) -> str:
        """Application name."""
        return self._name

    @property
    def settings(self) -> Settings:
        """Application settings."""
        return self._settings

    @classmethod
    def launch(
        cls,
        func: Func[ReturnT],
        *,
        name: Optional[str] = None,
        settings_class: Optional[Type[Settings]] = None,
    ) -> ReturnT:
        """Create app instance and run the given coroutine function."""
        # Set defaults for optional arguments
        if name is None:
            name = get_app_name(func)
        if settings_class is None:
            settings_class = get_settings_class(func)
        # Automatically fill in missing settings (e.g., from settings files)
        settings_class = autofill(name)(settings_class)
        # Create settings instance
        settings: Settings = settings_class()
        # Create and run app instance
        with cls(name, settings) as app:
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
        if issubclass(annotation, App):
            return self
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


def get_settings_class(func: Func[ReturnT]) -> Type[Settings]:
    """Try to get the settings class from the function signature."""
    spec = inspect.getfullargspec(func)
    for arg_name in spec.args:
        try:
            annotation = spec.annotations[arg_name]
        except KeyError:
            continue
        if issubclass(annotation, Settings):
            # Strangely, mypy can't infer that `annotation` has the right
            # type from the `issubclass` call. We explicitly cast as a
            # work-around to this.
            return cast(Type[Settings], annotation)
    # Default to the base settings class
    return Settings


def get_app_name(func: Func[ReturnT]) -> str:
    """Get the name of the running application."""
    # Use the function name itself if said name is descriptive
    if func.__name__ not in ("main",) and not func.__name__.startswith("_"):
        return func.__name__

    # If the function name isn't desciptive, we query the main module
    import __main__ as main  # type: ignore[import]  # pylint: disable=import-outside-toplevel

    # Use the module name if the application runs a module
    #
    # `main` will look something like this:
    #   main.__name__   : __main__
    #   main.__package__: baxter
    #   main.__file__   : /media/system/lib/python3.6/site-packages/baxter/__main__.py
    if isinstance(main.__package__, str):
        return main.__package__

    # Use the file name if the application runs directly
    #
    # `main` will look something like this:
    #   main.__name__   : __main__
    #   main.__package__: None
    #   main.__file__   : /media/system/bin/baxter
    #
    # Or, sometimes, like this:
    #   main.__file__   : _appster.py
    file_name = Path(main.__file__).stem  # Use the stem to avoid file extensions
    # Remove leading and trailing underscores (if any).
    # All in all, a file name like "_appster.py" becomes "appster".
    return file_name.strip("_")
