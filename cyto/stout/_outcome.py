from collections.abc import AsyncIterable, Iterable
from contextlib import AbstractAsyncContextManager
from typing import Annotated, Any

from pydantic import Field

from ..model import FrozenModel
from ._message import Message
from ._result_map import ResultMap
from .keynote import Keynote

Code = Annotated[str, Field(pattern="^[0-9]{4}$")]


# Result may be anything but *usually* it's a mapping that contains a `Keynote`.
OutcomeResult = ResultMap | Any


class Outcome(FrozenModel):
    """The result and/or messages from an execution."""

    # Note that `OutcomeResult` may be `Any` value. Even `None`.
    result: OutcomeResult = ResultMap()
    # Mapping of code (e.g. "1234") to message
    #
    # Note that mypy doesn't recognize `Code` as a type. It should be
    # `Type[str]`. For now, we simply ignore the error.
    messages: dict[Code, Message] = Field(  # type: ignore[valid-type]
        default_factory=dict,
    )

    def keynote(self) -> Keynote:
        """Return the keynote of the result (if any).

        Returns the empty keynote if there is no result.
        """
        try:
            return self.result.keynote
        except (TypeError, AttributeError):
            return Keynote()

    def result_is_final(self) -> bool:
        """There is a result (of a known type) in a final state (no further changes).

        Returns False if there is not result. E.g., if the keynote is empty.
        """
        if keynote := self.keynote():
            return keynote.finality == "final"
        return False

    def __bool__(self) -> bool:
        """Is this outcome with either a result or messages."""
        return bool(self.result) or bool(self.messages)

    def errors(self) -> Iterable[tuple[str, Message]]:
        """Return error messages (if any)."""
        return (
            (code, msg)
            for code, msg in self.messages.items()
            if msg.severity == "error"
        )

    def get_first_error(self) -> tuple[str, Message] | None:
        """Return the first error message (if any)."""
        try:
            return next(iter(self.errors()))
        except StopIteration:
            return None


OutcomeStream = AbstractAsyncContextManager[AsyncIterable[Outcome]]
