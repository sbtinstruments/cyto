from typing import Any, AsyncContextManager, AsyncIterable, Iterable

from pydantic import Field, constr

from ..model import FrozenModel
from ._message import Message
from ._result_map import ResultMap

Code = constr(regex="^[0-9]{4}$")


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
    messages: dict[Code, Message] = Field(default_factory=dict)  # type: ignore

    def result_is_final(self) -> bool:
        """There is a result (of a known type) without tentative values."""
        if not isinstance(self.result, ResultMap):
            return False
        return self.result.keynote.is_final()

    def is_empty(self) -> bool:
        """Is this outcome without result or messages."""
        return self.result is None and not self.messages

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


OutcomeStream = AsyncContextManager[AsyncIterable[Outcome]]
