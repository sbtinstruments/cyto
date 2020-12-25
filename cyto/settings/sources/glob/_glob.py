from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, MutableMapping, Protocol

from pydantic import BaseSettings

from ....basic import deep_update as dict_deep_update

# Note that we disable D102 for `Protocol`s since it's redundant documentation.
# Similarly, we disable too-few-public-methods since it doens't make sense for
# `Protocol`s. Hopefully, both pydocstyle and pylint will special-case `Protocol`s
# soon enough.


class Loader(Protocol):  # pylint: disable=too-few-public-methods
    """Given a settings file path, return a settings dict with the file content."""

    def __call__(self, __file: Path) -> MutableMapping[str, Any]:  # noqa: D102
        ...


# We don't need that many public methods for this small utility class.
# Maybe we can replace it with a function that returns a function.
# I'm just not sure that this is a better approach.
class GlobSource:  # pylint: disable=too-few-public-methods
    """Find setting files in a directory with a glob pattern."""

    def __init__(
        self, directory: Path, pattern: str, loader: Loader, *, deep_update: bool = True
    ):
        self._dir = directory
        self._pattern = pattern
        self._loader = loader
        # We can't do better than `[Any, Any]` for now because of `dict.update`'s
        # lacking signature.
        self._update_func: Callable[[Any, Any], None]
        if deep_update:
            self._update_func = dict_deep_update
        else:
            self._update_func = dict.update

    def __call__(self, _: BaseSettings) -> Dict[str, Any]:
        """Return a dict with settings from the globbed files."""
        result: Dict[str, Any] = {}
        for path in sorted(self._dir.glob(self._pattern)):
            self._update_func(result, dict(self._loader(path)))
        return result
