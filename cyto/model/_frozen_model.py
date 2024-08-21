from __future__ import annotations

from typing import Any, ClassVar, TypeVar

from mergedeep import Strategy, merge
from pydantic import BaseModel, ConfigDict

Derived = TypeVar("Derived", bound=BaseModel)


class FrozenModel(BaseModel):
    """Immutable model."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True,
        # `extra="forbid"` is not strictly necessary for immutability but it's a sound
        # default. It adds another layer of "strictness" that we expect in the context
        # of immutability.
        extra="forbid",
    )

    # TODO: Add root validator that ensure that all members are frozen as well

    def update(
        self: Derived, strategy: Strategy | None = None, /, **kwargs: Any
    ) -> Derived:
        """Return copy of this model updated with the given values.

        Unlike `BaseModel.copy(update=...)`, this function:

         * Validates the result.
         * Performs a deep merge (additive by default).

        """
        if strategy is None:
            strategy = Strategy.ADDITIVE
        # TODO: Optimize this function. I'm (FPA) sure that we can avoid an unnecessary
        # dict copy (probably many!) if we restructure or inline the implementation.
        patch = {
            key: value.model_dump() if isinstance(value, BaseModel) else value
            for key, value in kwargs.items()
        }
        unvalidated_dict = merge({}, self.model_dump(), patch, strategy=strategy)
        # For now, we simply call the constructor to trigger validation
        return type(self)(**unvalidated_dict)
