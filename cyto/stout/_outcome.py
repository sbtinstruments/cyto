from typing import Any

from pydantic import Field, constr

from ..model import FrozenModel
from ._message import Message

Code = constr(regex="^[0-9]{4}$")


class Outcome(FrozenModel):
    """The result and/or messages from an execution."""

    result: Any = None
    # Mapping of code (e.g. "1234") to message
    #
    # Note that mypy doesn't recognize `Code` as a type. It should be
    # `Type[str]`. For now, we simply ignore the error.
    messages: dict[Code, Message] = Field(default_factory=dict)  # type: ignore
