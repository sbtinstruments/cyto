import signal
from contextlib import asynccontextmanager
from typing import AsyncIterator

import anyio


@asynccontextmanager
async def cancel_on_signal() -> AsyncIterator[None]:
    """Enter cancel scope that cancels itself if we receive a signal."""
    async with anyio.create_task_group() as tg:
        # Listen for signals for the duration of this context manager.
        # If we receive a signal, we call `tg.cancel_scope.canel`.
        # This cancels both the listener task (`_cancel_on_signal`)
        # *and* the tasks within this context manager (code that runs
        # at the point of the `yield` statement).
        tg.start_soon(_cancel_on_signal, tg.cancel_scope)
        yield
        # If we get this far, this context manager exitted normally.
        # We cancel `tg.cancel_scope` so that the listener task
        # (`_cancel_on_signal`) doesn't block us.
        tg.cancel_scope.cancel()


async def _cancel_on_signal(cancel_scope: anyio.CancelScope) -> None:
    """Cancel the given cancel scope if we receive a signal."""
    with anyio.open_signal_receiver(signal.SIGTERM, signal.SIGINT) as signals:
        async for _ in signals:
            cancel_scope.cancel()
