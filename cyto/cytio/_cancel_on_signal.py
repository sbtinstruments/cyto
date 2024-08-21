import logging
import signal
import sys
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from typing import Literal

import anyio
from anyio.abc import TaskGroup, TaskStatus

_LOGGER = logging.getLogger(__name__)

_SignalAction = Literal["ignore", "cancel", "exit"]
_DEFAULT_SIGNAL_ACTIONS: dict[int, _SignalAction] = {
    signal.SIGINT: "cancel",
    signal.SIGTERM: "cancel",
    signal.SIGQUIT: "exit",
}


@asynccontextmanager
async def cancel_on_signal(
    *,
    ignore: Iterable[int] | int | None = None,
) -> AsyncIterator[None]:
    """Enter cancel scope that cancels itself if we receive a signal.

    This overrides any existing signal handler.
    """
    signal_actions = _get_signal_actions(ignore=ignore)
    async with anyio.create_task_group() as tg:  # noqa: SIM117
        # Listen for signals for the duration of this context manager.
        # If we receive a signal, we call `tg.cancel_scope.cancel`.
        # This cancels both the listener task (`_cancel_on_signal`)
        # *and* the tasks within this context manager (code that runs
        # at the point of the `yield` statement).
        async with _listener(tg, signal_actions):
            yield


def _get_signal_actions(
    *,
    ignore: Iterable[int] | int | None = None,
) -> dict[int, _SignalAction]:
    # Normalize the `ignore` argument
    match ignore:
        case None:
            ignore = frozenset()
        case int():
            ignore = frozenset((ignore,))
        case _:
            ignore = frozenset(ignore)
    return {
        signal: "ignore" if signal in ignore else action
        for signal, action in _DEFAULT_SIGNAL_ACTIONS.items()
    }


@asynccontextmanager
async def _listener(
    tg: TaskGroup, signal_actions: dict[int, _SignalAction]
) -> AsyncIterator[None]:
    # The `_cancel_on_signal` action runs within the shielded `listener_scope` cancel
    # scope. If we didn't shield it, the very first SIGINT/SIGTERM would cancel it.
    # We don't want that. We want `_cancel_on_signal` to keep running while `tg_scope`
    # cancels. This way, we can react to signals during the cancellation phase of
    # `tg_scope`.
    tg_scope = tg.cancel_scope
    listener_scope = await tg.start(_apply_action_on_signal, tg_scope, signal_actions)
    assert isinstance(listener_scope, anyio.CancelScope)
    try:
        yield
    finally:
        # At this point, the `tg_scope` cancellation phase is over. We no longer
        # require the signal listener. It runs within the shielded  `listener_scope`
        # so it never saw the `tg_scope` cancellation. We cancel `tg_scope` manually.
        listener_scope.cancel()


async def _apply_action_on_signal(
    tg_scope: anyio.CancelScope,
    signal_actions: dict[int, _SignalAction],
    *,
    task_status: TaskStatus[anyio.CancelScope] = anyio.TASK_STATUS_IGNORED,
) -> None:
    """Cancel the outer cancel scope if we receive a signal."""
    with anyio.CancelScope(shield=True) as listener_scope:
        task_status.started(listener_scope)
        with anyio.open_signal_receiver(*signal_actions) as received_signals:  # type: ignore[arg-type]
            async for signal_no in received_signals:
                action = signal_actions[signal_no]
                _apply_signal_action(signal_no, action, tg_scope)


def _apply_signal_action(
    signal_no: int, action: _SignalAction, tg_scope: anyio.CancelScope
) -> None:
    signal_name = signal.Signals(signal_no).name
    match action:
        case "ignore":
            _LOGGER.info("Received %s signal. We ignore this signal.", signal_name)
        case "cancel":
            if tg_scope.cancel_called:
                _LOGGER.info(
                    "Received %s signal. Task group already cancelled. "
                    "Doing nothing. Use SIGQUIT (CTRL+\\) to exit immediately "
                    "without proper cleanup.",
                    signal_name,
                )
            else:
                _LOGGER.info(
                    "Received %s signal. Will cancel task group and exit gracefully.",
                    signal_name,
                )
                tg_scope.cancel()
        case "exit":
            _LOGGER.info(
                "Received %s signal. Will exit immediately without proper cleanup.",
                signal_name,
            )
            sys.exit()
        case _:
            _LOGGER.error(
                "Received %s signal. Unknown signal action '%s'. We do nothing.",
                signal_name,
                action,
            )
