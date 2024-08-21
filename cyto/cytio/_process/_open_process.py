from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import asynccontextmanager, suppress
from datetime import timedelta
from os import PathLike
from subprocess import PIPE
from time import perf_counter
from typing import (
    IO,
    Any,
    Generic,
    TypeVar,
)

import anyio
from anyio.abc import Process

from .._task_context import TaskContext

T = TypeVar("T")
_LOGGER = logging.getLogger(__name__)


class ProcessContext(  # pylint: disable=too-few-public-methods
    TaskContext[T], Generic[T]
):
    """This is a workaround for mypy to get proper typing in derived classes."""


@asynccontextmanager
async def open_process(  # noqa: PLR0913
    command: str | bytes | Sequence[str | bytes],
    *,
    stdin: int | IO[Any] | None = PIPE,
    stdout: int | IO[Any] | None = PIPE,
    stderr: int | IO[Any] | None = PIPE,
    cwd: str | bytes | PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    start_new_session: bool = False,
    kill_delay: timedelta | None = None,
) -> AsyncIterator[Process]:
    """Run the given command in a subprocess.

    In addition to the semantics of `async with await anyio.open_process()`, this
    context manager:

     * Waits for the process on normal `__aexit__` (i.e., when there is no exception)
     * Terminates the process on exception:
        * Starts gracefully with a SIGTERM
        * Closes stdin (let the process now that we have no more input for it)
        * Waits `kill_delay` seconds for the process to wind down (e.g., write it's
          last items on stdout/stderr).
        * If the process is still up, we now send SIGKILL (immediate shutdown)
        * In any case, we close stdout and stderr and wait for the process to exit.

    Basically, we wrap `anyio.open_process` to make the semantics more like
    `anyio.create_task_group`.

    Inspired by:
    https://github.com/sbtinstruments/wright/blob/d13b57613f2ca4245012d8b25193777657194050/wright/subprocess/_subprocess.py

    ## Note on `CTRL+C` in the terminal

    When you press `CTRL+C` in the terminal, it sends SIGTERM to *all* processes
    in the foreground process group. Per default, all child processes belong to
    the same process group as their parent. In turn, both the parent process and
    all child processes receive SIGTERM whenever someone presses `CTRL+C`.

    Maybe that's what you want. Maybe it is not.

    If you don't want this behaviour, the solution is to use a separate process
    group for the child processes. The current anyio API doesn't expose this
    functionality. We can, however, use `start_new_session=True` to indirectly
    create a new process group. It's a bit crude but it works. For now, that's
    the recommended way to opt-out of the terminals's SIGTERM-happy `CTRL+C`
    semantics.

    Here is a nice primer on terminals, process groups, sessions, CTRL+C, etc.:
    https://biriukov.dev/docs/fd-pipe-session-terminal/3-process-groups-jobs-and-sessions/
    """
    if kill_delay is None:
        kill_delay = timedelta(seconds=1)
    process = await anyio.open_process(
        command,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        cwd=cwd,
        env=env,
        start_new_session=start_new_session,
    )
    try:
        yield process
        await process.wait()
    except BaseException:
        # Try to gracefully terminate the process.
        # Raises `ProcessLookupError` if the process already exited. We suppress
        # this error, since it simply means that our job is done.
        with suppress(ProcessLookupError):
            process.terminate()
        raise
    finally:
        finally_begin = perf_counter()
        # Close stdin to let the process now that we have no more input for it.
        if process.stdin is not None:
            # No `move_on_after` here, since `aclose` really just calls the sync
            # `close` method underneath. At some point, anyio will probably expose
            # said sync method directly.
            with anyio.CancelScope(shield=True):
                await process.stdin.aclose()
        # Give the process some time to exit.
        #
        # Note that some processes may give some final output when they
        # receive a signal. E.g., "The user interrupted the program" on SIGTERM.
        # Therefore, this is also an opportunity to catch this final output
        # before we close the stdout and stderr streams at [2].
        # If we don't do this, we get some nasty `AssertionError`s from
        # deep within asyncio about "feed_data after feed_eof". This is
        # because we close the stream (at [2]) while there is still some
        # final output from the process in flux.
        #
        # Shield this, because the parent task may be cancelled (and if this
        # is the case, the `process.wait` call fails immediately without
        # shielding).
        _LOGGER.debug(
            "We wait %.1f seconds for process (pid=%d) to exit gracefully",
            kill_delay.total_seconds(),
            process.pid,
        )
        with anyio.move_on_after(
            kill_delay.total_seconds(), shield=True
        ) as scope:  # [1]
            await process.wait()
        exited_gracefully = not scope.cancel_called
        # Warn the user if the process didn't terminate gracefully. This is
        # really something that they should deal with! E.g., increase the
        # `kill_delay` appropriately.
        if not exited_gracefully:
            _LOGGER.warning(
                "Tried to terminate process (pid=%d) gracefully (with SIGTERM). "
                "The process did not exit within the expected %.1f seconds. "
                "We kill the process now (SIGKILL). "
                "Try to increase 'kill_delay' to avoid this situation.",
                process.pid,
                kill_delay.total_seconds(),
            )
        # If the process already stopped (gracefully), this does nothing.
        # Otherwise, it kills the process for good.
        with suppress(ProcessLookupError):
            process.kill()
        # Close the output streams (stdout and stderr) and wait for the
        # process to exit (again).
        # Shield this for the same reason as given for [1].
        with anyio.CancelScope(shield=True):
            await process.aclose()  # [2]
        finally_end = perf_counter()
        finally_duration = finally_end - finally_begin
        _LOGGER.debug(
            "Process (pid=%d) exited (gracefully=%s) after %.3f seconds",
            process.pid,
            exited_gracefully,
            finally_duration,
        )
