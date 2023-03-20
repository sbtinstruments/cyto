import logging
import signal
from contextlib import asynccontextmanager
from typing import AsyncIterator

import anyio

_LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def cancel_on_signal() -> AsyncIterator[None]:
    """Enter cancel scope that cancels itself if we receive a signal.

    This overrides any existing signal handler.
    """
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
    with anyio.open_signal_receiver(
        signal.SIGTERM, signal.SIGINT  # , signal.SIGPIPE
    ) as signals:
        async for signal_no in signals:
            signal_name = signal.Signals(signal_no).name
            _LOGGER.debug("Received %s signal. Will cancel task group.", signal_name)
            cancel_scope.cancel()
