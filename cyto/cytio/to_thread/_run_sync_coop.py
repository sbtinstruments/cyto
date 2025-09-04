import logging
from collections.abc import Callable
from threading import Event

import anyio
import anyio.to_thread
from anyio.abc import CapacityLimiter

_LOGGER = logging.getLogger(__name__)


async def run_sync_coop[*PosArgsT, T_Retval](
    func: Callable[[Event, *PosArgsT], T_Retval],
    *args: *PosArgsT,
    limiter: CapacityLimiter | None = None,
) -> T_Retval:
    """Call the given function with the given arguments in a worker thread.

    This is a cooperative version of `anyio.to_thread.run_sync`. The given `func`
    _must_ accept a `threading.Event` as the first argument. It is the responsibility
    of `func` to check this event every now and then and stop if the event is set.
    Example cooperative `func`:

        def my_cooperative_func(stop_event: threading.Event) -> None:
            import time

            while True:
                if stop_event.is_set():
                    break

                time.sleep(3)  # Pretend to do some IO-intensive work

    Note how `my_cooperative_func` checks if `stop_event` is set every now and then.
    This cooperation enables graceful shutdown.
    """
    stop_event = Event()

    async with anyio.create_task_group() as tg:
        tg.start_soon(_set_event_on_exit, stop_event)
        try:
            return await anyio.to_thread.run_sync(
                func, stop_event, *args, limiter=limiter
            )
        finally:
            # When `func` returns, we cancel the `_set_event_on_exit` task so
            # that it doesn't block the execution from returning.
            tg.cancel_scope.cancel()

    # If we get here, it means that the task group was cancelled by
    # the stop event.
    raise anyio.get_cancelled_exc_class()("Cancelled by stop event")


async def _set_event_on_exit(stop_event: Event) -> None:
    try:
        await anyio.sleep_forever()
    finally:
        stop_event.set()
