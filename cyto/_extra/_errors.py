from __future__ import annotations

from typing import Any


class ExtraError(Exception):
    """Base exception for all extra-related errors."""

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

    @classmethod
    def from_module_name(cls, module_name: str) -> ExtraImportError:
        """Resolve "extra" name from the module name.

        Usually, you call this function like:

            try:
                from ._my_local_module import MyFancyClass
                from ._my_utils import do_the_thing
            except ImportError as exc:
                from .._extra import ExtraImportError

                raise ExtraImportError.from_module_name(__name__) from exc

        from with `__init__.py` or similar.
        """
        # We use `[1:]` to skip the `cyto` part
        extra_name = "-".join(module_name.split(".")[1:])
        return cls(extra_name)
