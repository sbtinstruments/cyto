from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Optional

import toml
from pydantic import BaseSettings

from ..basic import deep_update as dict_deep_update


# We don't need that many public methods for this small utility class.
# Maybe we can replace it with a function that returns a function.
# I'm just not sure that this is a better approach.
class GlobSource:  # pylint: disable=too-few-public-methods
    """Find setting files in a directory with a glob pattern."""

    def __init__(self, directory: Path, pattern: str, *, deep_update: bool = True):
        self._dir = directory
        self._pattern = pattern
        # We can't do better than `[Any, Any]` for now because of `dict.update`'s
        # lacking signature.
        self._update_func: Callable[[Any, Any], None]
        if deep_update:
            self._update_func = dict_deep_update
        else:
            self._update_func = dict.update

    def __call__(self, _: BaseSettings) -> Dict[str, Optional[str]]:
        env_vars: Dict[str, Optional[str]] = {}
        for path in sorted(self._dir.glob(self._pattern)):
            self._update_func(env_vars, toml.load(path))
        return env_vars
