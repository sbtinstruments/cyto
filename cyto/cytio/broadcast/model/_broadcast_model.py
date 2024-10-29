from __future__ import annotations

import logging
from typing import Any, TypeVar

from ....model import FrozenModel, ValidationMode
from .._broadcast_value import BroadcastValue, MaybeValue, NoValue

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T", bound=FrozenModel)


class BroadcastModel(BroadcastValue[T]):
    """Broadcast of a model that publishes on each change to said model."""

    def __init__(self, value: MaybeValue[T] = NoValue) -> None:
        super().__init__(value=value)

    def frozen_patch(
        self,
        patch: dict[str, Any],
        *,
        validation: ValidationMode | None = None,
    ) -> None:
        """Make changes to this model.

        Automatically publishes the changes.
        """
        if self.latest_value is NoValue:
            raise RuntimeError(
                "You must initialize this broadcast before you can mutate it"
            )
        assert isinstance(self.latest_value, FrozenModel)
        new_value = self.latest_value.frozen_patch(patch, validation=validation)
        self.publish(new_value)  # type: ignore[arg-type]
