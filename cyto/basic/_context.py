from __future__ import annotations

from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    AsyncExitStack,
    ExitStack,
)
from types import TracebackType
from typing import Self


class AsyncContextStack(AbstractAsyncContextManager["AsyncContextStack"]):
    """Combine several context managers into one via an AsyncExitStack."""

    def __init__(self) -> None:
        self._stack: AsyncExitStack | None = None

    async def _aenter_stack(self, stack: AsyncExitStack) -> None:
        """Add context managers to the underlying stack.

        A child class should override this function.
        """

    async def __aenter__(self) -> Self:
        # This is the exception-safe "enter and pop" idiom (coined 2022 by FPA).
        # The whole purpose of `AsyncContextStack` is to consistently apply the
        # enter and pop idiom throughout your code base.
        async with AsyncExitStack() as stack:
            await self._aenter_stack(stack)
            self._stack = stack.pop_all()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        assert self._stack is not None
        return await self._stack.__aexit__(exc_type, exc_value, traceback)


class ReentrantAsyncContextStack(AsyncContextStack):
    """Reentrant (and reusable) version of the async context stack."""

    def __init__(self) -> None:
        super().__init__()
        self._enter_count = 0

    async def __aenter__(self) -> Self:
        self._enter_count += 1
        if self._enter_count != 1:
            return self
        await super().__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        self._enter_count -= 1
        if self._enter_count != 0:
            return None
        try:
            return await super().__aexit__(exc_type, exc_value, traceback)
        finally:
            # Prepare this class for reuse
            self._stack = None


class ContextStack(AbstractContextManager["ContextStack"]):
    """Combine several context managers into one via an ExitStack."""

    def __init__(self) -> None:
        self._stack: ExitStack | None = None

    def _enter_stack(self, stack: ExitStack) -> None:
        """Add context managers to the underlying stack.

        A child class should override this function.
        """

    def __enter__(self) -> Self:
        # This is the exception-safe "enter and pop" idiom (coined 2022 by FPA).
        # The whole purpose of `ContextStack` is to consistently apply the
        # enter and pop idiom throughout your code base.
        with ExitStack() as stack:
            self._enter_stack(stack)
            self._stack = stack.pop_all()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        assert self._stack is not None
        return self._stack.__exit__(exc_type, exc_value, traceback)


class ReentrantContextStack(ContextStack):
    """Reentrant (and reusable) version of the  context stack."""

    def __init__(self) -> None:
        super().__init__()
        self._enter_count = 0

    def __enter__(self) -> Self:
        self._enter_count += 1
        if self._enter_count != 1:
            return self
        super().__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        self._enter_count -= 1
        if self._enter_count != 0:
            return None
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            # Prepare this class for reuse
            self._stack = None
