from __future__ import annotations

from collections.abc import Callable, Coroutine
from contextlib import AbstractAsyncContextManager
from types import TracebackType
from typing import Any, Self

import anyio
from anyio.abc import TaskGroup


class ReusableTaskGroup(AbstractAsyncContextManager["ReusableTaskGroup"]):
    """Reusable (but not reentrant) task group."""

    def __init__(self) -> None:
        self._tg: TaskGroup | None = None
        self._lock = anyio.Lock()

    def start_soon(
        self, func: Callable[..., Coroutine[Any, Any, Any]], *args: Any, **kwargs: Any
    ) -> None:
        if self._tg is None:
            raise RuntimeError("Call ReusableTaskGroup.__aenter__first")
        self._tg.start_soon(func, *args, **kwargs)

    async def clear(self) -> None:
        """Cancel all tasks (if any).

        Raises in the same manner as __aexit__.

        ## Avoid cancel scope stack corruption!

        We do exactly what the anyio documentation tells us to avoid:

        > Manually calling CancelScope.__enter__() and CancelScope.__exit__(),
        > usually from another context manager class, in the wrong order

        See:
        https://anyio.readthedocs.io/en/stable/cancellation.html#avoiding-cancel-scope-stack-corruption

        When you call `ReusableTaskGroup.clear`, you actually call
        `TaskGroup.__aexit__` closely followed by `TaskGroup.__aenter__`. In turn,
        this calls the underlying exit/enter functions of `CancelScope`.

        It's the responsibility of the caller to ensure that calls to `clear` does
        not mess up the "normal" order of enter/exit calls.

        ### Example of good code

        This is good code:

        ```python

        async with ReusableTaskGroup() as rtg:  # (a)
            rtg.start_soon(...)
            rtg.start_soon(...)
            await rtg.clear()  # (b,c)
            rtg.start_soon(...)
            rtg.start_soon(...)
            await rtg.clear()  # (d,e)
            rtg.start_soon(...)
            rtg.start_soon(...)
            # (f)
        ```

        The good code results in this enter/exit call order:

         a. enter
         b. exit
         c. enter
         d. exit
         e. enter
         f. exit

        That's fine, because it's semantically equivalent to a series of
        regular `async with create_task_group()` statements:

        ```python
        async with TaskGroup() as tg:  # (a)
            tg.start_soon(...)
            tg.start_soon(...)
            tg.cancel_scope.cancel()
            # (b)
        async with TaskGroup() as tg:  # (c)
            tg.start_soon(...)
            tg.start_soon(...)
            tg.cancel_scope.cancel()
            # (d)
        async with TaskGroup() as tg:  # (e)
            tg.start_soon(...)
            tg.start_soon(...)
            tg.cancel_scope.cancel()
            # (f)
        ```

        ### Example of *bad* code (do *not* do this!)

        This is bad code:

        ```python
        # BAD CODE! Do not write code like this.
        async with ReusableTaskGroup() as rtg1:  # (a)
            rtg1.start_soon(...)
            rtg1.start_soon(...)
            async with ReusableTaskGroup() as rtg2:  # (b)
                rtg2.start_soon(...)
                rtg2.start_soon(...)
                # THIS IS BAD!
                await rtg1.clear()  # (c,d)
                # (e)
            # (f)
        ```

        The bad code results in this enter/exit call order:

         a. rtg1 enter
         b. rtg2 enter
         c. rtg1 exit (this is where things go wrong)
         d. rtg1 enter
         e. rtg2 exit
         f. rtg1 exit

        It's *not* possible to get this enter/exit order with a series
        regular `async with create_task_group()` statements. Therefore,
        it is bad code. It results in cancel scope corruption.
        """
        if self._tg is None:
            raise RuntimeError("Call ReusableTaskGroup.__aenter__first")
        # We may hit a schedule point so we safeguard this whole method with a lock
        # to avoid race conditions.
        async with self._lock:
            try:
                self._tg.cancel_scope.cancel()
                # May raise!
                await self.__aexit__(None, None, None)
            finally:
                assert self._tg is None
                # Never raises (unless cancelled) since we are sure that `_tg` is
                # None.
                await self.__aenter__()

    async def __aenter__(self) -> Self:
        if self._tg is not None:
            raise RuntimeError("ReusableTaskGroup is not reentrant")
        self._tg = await anyio.create_task_group().__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        assert self._tg is not None
        try:
            return await self._tg.__aexit__(exc_type, exc_value, traceback)
        finally:
            self._tg = None
