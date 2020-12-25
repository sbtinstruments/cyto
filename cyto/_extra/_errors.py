from typing import Any


class ExtraError(Exception):
    """Base exception for all extra-related erorrs."""

    def __init__(self, extra_name: str, *args: Any) -> None:
        super().__init__(*args)
        self._extra_name = extra_name


class ExtraImportError(ExtraError, ImportError):
    """The extra depends on a component that isn't available."""

    def __init__(self, extra_name: str) -> None:
        msg = (
            f'The "{extra_name}" extra depends on a component that isn\'t available. '
            f'Did you forget to specify the "{extra_name}" extra during install? '
            f'Try again with, e.g., "poetry install --extras {extra_name}"'
        )
        super().__init__(extra_name, msg)
