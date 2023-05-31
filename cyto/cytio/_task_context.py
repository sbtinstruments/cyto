from __future__ import annotations

from contextlib import AsyncExitStack
from typing import Generic, TypeVar

import anyio
from anyio.abc import TaskGroup

from ..basic import AsyncContextStack

T = TypeVar("T")


class TaskContext(  # pylint: disable=too-few-public-methods
    AsyncContextStack[T], Generic[T]
):
    """`AsyncContextStack` with a built-in `TaskGroup` for background work.

    That's it. Don't need the `TaskGroup`? Just use a regular `AsyncContextStack`.

    ## Avoid cancel scope stack corruption!

    Any context managager that includes a `CancelScope` (often indirectly) is
    vulnerable to cancel scope stack corruption. It's the responsibility of the caller
    to avoid this.

    Generally, only use `TaskContext` in a manner that's semantically equivalent
    to regular `async with TaskContext()` statements.

    Follow the very same guidelines as for a "naked" `CancelScope` found here:
    https://anyio.readthedocs.io/en/stable/cancellation.html#avoiding-cancel-scope-stack-corruption
    """

    def __init__(self) -> None:
        super().__init__()
        self._tg: TaskGroup | None = None

    async def _aenter_stack(self, stack: AsyncExitStack) -> None:
        await super()._aenter_stack(stack)
        self._tg = await stack.enter_async_context(anyio.create_task_group())

    # TODO: Remove when `AsyncContextStack.__aenter__` returns `typing.Self`
    # in Python 3.11.
    async def __aenter__(self) -> T:
        await super().__aenter__()
        return self  # type: ignore[return-value]
