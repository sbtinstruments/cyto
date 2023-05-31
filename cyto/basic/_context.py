from __future__ import annotations

from contextlib import AbstractAsyncContextManager, AsyncExitStack
from types import TracebackType
from typing import Generic, TypeVar

T = TypeVar("T")


class AsyncContextStack(AbstractAsyncContextManager[T], Generic[T]):
    """Combine several context managers into one via an AsyncExitStack."""

    def __init__(self) -> None:
        self._stack: AsyncExitStack | None = None

    async def _aenter_stack(self, stack: AsyncExitStack) -> None:
        """Add context managers to the underlying stack.

        A child class should override this function.
        """

    # TODO: Replace return type with `typing.Self` in Python 3.11
    async def __aenter__(self) -> T:
        # This is the exception-safe "enter and pop" idiom (coined 2022 by FPA).
        # The whole purpose of `AsyncContextStack` is to consistently apply the
        # enter and pop idiom throughout your code base.
        async with AsyncExitStack() as stack:
            await self._aenter_stack(stack)
            self._stack = stack.pop_all()
        return self  # type: ignore[return-value]

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        assert self._stack is not None
        return await self._stack.__aexit__(exc_type, exc_value, traceback)
