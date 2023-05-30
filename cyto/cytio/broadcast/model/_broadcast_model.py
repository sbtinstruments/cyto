from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator, TypeVar

from ....model import FrozenModel
from .._broadcast_value import BroadcastValue, MaybeValue, NoValue

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T", bound=FrozenModel)


class BroadcastModel(BroadcastValue[T]):
    def __init__(self, value: MaybeValue[T] = NoValue) -> None:
        super().__init__(value=value)

    @contextmanager
    def mutate(self) -> Iterator[dict[str, Any]]:
        if self.latest_value is NoValue:
            raise RuntimeError(
                "You must initialize this broadcast before you can mutate it"
            )
        assert isinstance(self.latest_value, FrozenModel)
        mutable_value = self.latest_value.dict()
        try:
            yield mutable_value
        finally:
            new_value = type(self.latest_value)(**mutable_value)
            self.set(new_value)
