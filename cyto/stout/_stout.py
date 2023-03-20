from __future__ import annotations

import os
import sys
from io import TextIOBase
from typing import AsyncIterable, Literal

from ..model import FrozenModel
from ._outcome import Outcome
from ._outline import Outline

Status = Literal["pending", "running", "completed", "failed", "cancelled", "abandoned"]


def is_status_current(status: Status) -> bool:
    """Is this a current (i.e., not stopped) execution."""
    return status in ("pending", "running")


# We use these `FooSwig` to disambiguate between different "messages"/"chunks"
# in the stout stream. Disambiguate, in the sense that the presence of, e.g.,
# the "status" key clearly indicates that this is a "status update message".
# The new line-delimited stream looks like this:
#
#     {"status": "running"}
#     {"outcome": {"result": ..., "messages": {...}}
#     {"outline": {"trail": {...}}}
#     {"outline": {"trail": {...}}}
#     {"status": "cancelled"}
#
# This is similar to the "discriminated union" feature of Pydantic. We chose
# not to use discriminated unions, because the new line-delimited stream
# looks like this:
#
#     {"message_type": "status", "value": "running"}
#     {"message_type": "outcome", "result": ..., "messages": {...}
#     {"message_type": "outline", "trail": {...}}
#     {"message_type": "outline", "trail": {...}}
#     {"message_type": "status", "value": "cancelled"}
#     ...
#
# Where `message_type` is the discriminated value. This is too verbose for our
# liking and we don't gain anything *as long as the messages are distinct in their
# own right*. That's the case so far.
class _SwigBase(FrozenModel):
    def write(
        self, io: TextIOBase | None = None, *, append_newline: bool | None = None
    ) -> None:
        """Serialize this swig and write it to the given IO stream.

        Appends a newline character if `append_newline` is True (this is the default).

        Uses stdout per default. Assumes that this stream is still open.
        """
        if io is None:
            io = sys.stdout
        if append_newline is None:
            append_newline = True
        sys.stdout.write(self.json())
        sys.stdout.write(os.linesep)


class StatusSwig(_SwigBase):
    """Overall execution status and details."""

    status: Status
    executable_uri: str | None = None
    handle_uri: str | None = None

    @classmethod
    def from_current_process(cls) -> StatusSwig:
        """Return the status of the current process."""
        pid = os.getpid()
        return cls(status="running", handle_uri=f"process-id:{pid}")


class OutcomeSwig(_SwigBase):
    """Combination of result (if any) and messages (if any)."""

    outcome: Outcome


class OutlineSwig(_SwigBase):
    """Plan and (indirectly) the progress of said plan."""

    outline: Outline


Swig = StatusSwig | OutcomeSwig | OutlineSwig

Stout = AsyncIterable[Swig]
