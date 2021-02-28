import sys
from typing import Any

import pytest


class Argv:
    def __init__(self, monkeypatch: Any) -> None:
        self._monkeypatch = monkeypatch
        self._sys_argv_first = sys.argv[0]
        self.clear()

    def assign(self, *args: Any) -> None:
        """Clear existing arguments first and append the given ones."""
        self.clear()
        self.append(*args)

    def clear(self) -> None:
        self._argv = [self._sys_argv_first]
        self._update()

    def append(self, *args: Any) -> None:
        self._argv += args
        self._update()

    def _update(self) -> None:
        self._monkeypatch.setattr(sys, "argv", self._argv)


@pytest.fixture()
def argv(monkeypatch: Any) -> Argv:
    """Clear process arguments and return a helper object to add other args."""
    return Argv(monkeypatch)
