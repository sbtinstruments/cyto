from __future__ import annotations

import logging
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_core import from_json
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
)

from ....basic import count_leaves
from ....basic import deep_update as dict_deep_update

_LOGGER = logging.getLogger(__name__)


class GlobSource(PydanticBaseSettingsSource):
    """Find setting files in a directory with a glob pattern."""

    def __init__(
        self,
        settings_cls: type[BaseSettings],
        directory: Path,
        pattern: str,
        *,
        deep_update: bool = True,
    ):
        super().__init__(settings_cls)
        self._dir = directory
        self._pattern = pattern
        # We can't do better than `[Any, Any]` for now because of `dict.update`'s
        # lacking signature.
        self._update_func: Callable[[Any, Any], None]
        if deep_update:
            # TODO: Replace with `mergedeep`
            self._update_func = dict_deep_update
        else:
            self._update_func = dict.update

    # We must implement `get_field_value` since it's an abstract method.
    # It is never used in practice, however, so we simply return literals.
    #
    # See: https://github.com/pydantic/pydantic-settings/issues/102
    def get_field_value(
        self, _field: FieldInfo, _field_name: str
    ) -> tuple[Any, str, bool]:
        return None, "", False

    def __call__(self) -> dict[str, Any]:
        """Return a dict with settings from the globbed files."""
        result: dict[str, Any] = {}
        for path in sorted(self._dir.glob(self._pattern)):
            try:
                # For now, we simply load everything into memory up front.
                # Settings files are usually small, so this shouldn't be
                # a problem in practice. In turn, it makes it easier to
                # support different loaders.
                data = path.read_text(encoding="utf8")
            except (OSError, UnicodeDecodeError) as exc:
                _LOGGER.warning(
                    "We skip settings file '%s' because we can not read it: %s",
                    path,
                    exc,
                )
                continue
            try:
                settings = _load_data(path, data)
            except (ValueError, TypeError) as exc:
                _LOGGER.warning(
                    "We skip settings file '%s' because we can not parse it: %s",
                    path,
                    exc,
                )
                continue
            _LOGGER.debug("Got %d setting(s) from '%s'", count_leaves(settings), path)
            self._update_func(result, settings)
        return result


def _load_data(path: Path, data: str) -> dict[str, Any]:
    match path.suffix:
        case ".json":
            result = from_json(data)
            if not isinstance(result, dict):
                raise TypeError("Invalid type returned from JSON loader")
            return result
        case ".toml":
            return tomllib.loads(data)
        case other:
            raise ValueError(f"Unknown file suffix: '{other}'")
