from __future__ import annotations

import logging
import os
from collections.abc import Callable, Coroutine, Sequence
from contextlib import AsyncExitStack
from functools import wraps
from logging import Logger
from subprocess import PIPE
from typing import IO, Any, Generic, TypeVar

import anyio
from anyio.abc import ByteReceiveStream, Process

from .._task_context import TaskContext
from ._open_process import open_process

T = TypeVar("T")
_LOGGER = logging.getLogger(__name__)

StreamReceiver = Callable[..., Coroutine[Any, Any, Any]]


class ProcessContext(TaskContext[T], Generic[T]):
    """Higher-level features on top of the low-level `open_process`.

    Use in a similar fashion as `TaskContext`.

    Blocks on exit until the process exits. Sends SIGTERM to the process
    if an exception occurs.
    """

    def __init__(
        self,
        command: str | bytes | Sequence[str | bytes],
        *,
        stdin: int | IO[Any] | None = PIPE,
        stdout: int | IO[Any] | Logger | None = PIPE,
        stderr: int | IO[Any] | Logger | None = PIPE,
        **kwargs: Any,
    ) -> None:
        super().__init__()
        # Save all the arguments for the `open_process` call later.
        self._command = command
        self._stdin = stdin
        self._stdout = stdout
        self._stderr = stderr
        self._kwargs = kwargs  # We don't care about the rest
        # Handle to the process that we manage
        self._process: Process | None = None
        # Registered output stream (stdout and stderr) receivers
        self._stream_receivers: dict[ByteReceiveStream, StreamReceiver] = {}

    @property
    def pid(self) -> int:
        """Return the process ID (PID)."""
        if self._process is None:
            raise RuntimeError("Call __aenter__ first")
        return self._process.pid

    @property
    def returncode(self) -> int | None:
        """Return the return/exit code of this process.

        Returns None if this process is not yet done.
        """
        if self._process is None:
            raise RuntimeError("Call __aenter__ first")
        return self._process.returncode

    @property
    def stdout(self) -> ByteReceiveStream | None:
        """Return stdout of this process (if any)."""
        if self._process is None:
            raise RuntimeError("Call __aenter__ first")
        return self._process.stdout

    @property
    def stderr(self) -> ByteReceiveStream | None:
        """Return stderr of this process (if any)."""
        if self._process is None:
            raise RuntimeError("Call __aenter__ first")
        return self._process.stderr

    def start_receiver(
        self,
        receiver: StreamReceiver,
        stream: ByteReceiveStream | None,
        *args: Any,
        shield: bool | None = None,
    ) -> None:
        """Start task with stdout/stderr as it's first argument.

        `stream` must be one of `self.stdout` or `self.stderr`. We pass on `args`
        as-is to `receiver`.

        The lifetime of the task ties to the lifetime of this process.

        Note that `shield=True` per default. In other words, it's your responsibility
        to ensure that the coroutine returns when the stream closes. If not, the task
        blocks forever in `ProcessContext.__aexit__`.
        """
        if self._process is None or self._tg is None:
            raise RuntimeError("Call __aenter__ first")
        if stream is None:
            receiver_name = receiver.__name__
            raise RuntimeError(
                f"Can not start {receiver_name} since there given stream is None. "
                f"Did you forget to request a pipe for the stream?"
            )
        if stream is self._process.stdout:
            name = "stdout"
        elif stream is self._process.stderr:
            name = "stderr"
        else:
            raise ValueError("The given stream does not belong to this process.")

        try:
            existing_receiver = self._stream_receivers[stream]
        except KeyError:
            pass
        else:
            receiver_name = existing_receiver.__name__
            raise RuntimeError(
                f"Already registered '{receiver_name}' as the receiver for {name}. "
                "There can only be one receiver per output stream."
            )
        # Note that `shield=True` per default!
        #
        # We rely on the `open_process()` context manager to close the stream on exit.
        # In turn, this *should* make the receiver exit. With that in mind, it's safe
        # to wrap the entire thing in a shielded cancel scope. This way, we'll drain
        # the stream entirely even if cancellation occurs.
        #
        # We emphasize *should*, because we can't control what the user-provided
        # receiver does. If your receiver does not exit when the stream closes, then
        # explicitly set `shield=False`.
        if shield is None:
            shield = True

        _receiver: Callable[[ByteReceiveStream], Coroutine[Any, Any, Any]]
        if shield:

            @wraps(receiver)
            async def _shielded_receiver(stream: ByteReceiveStream, *args: Any) -> None:
                with anyio.CancelScope(shield=True):
                    await receiver(stream, *args)

            _receiver = _shielded_receiver
        else:
            _receiver = receiver

        self._tg.start_soon(_receiver, stream, *args)
        self._stream_receivers[stream] = _receiver

    async def wait(self) -> None:
        """Wait for this process to exit.

        Does not cancel/stop/terminate/kill this process. Merely waits for it to
        exit. That may never happen.
        """
        if self._process is None:
            raise RuntimeError("Call __aenter__ first")
        await self._process.wait()

    async def _aenter_stack(self, stack: AsyncExitStack) -> None:
        # TODO: This function could really use some cleanup.
        await super()._aenter_stack(stack)
        assert self._tg is not None

        stdout = PIPE if isinstance(self._stdout, Logger) else self._stdout
        stderr = PIPE if isinstance(self._stderr, Logger) else self._stderr

        self._process = await stack.enter_async_context(
            open_process(
                self._command,
                stdin=self._stdin,
                stdout=stdout,
                stderr=stderr,
                **self._kwargs,
            )
        )

        if isinstance(self._stdout, Logger):
            self.start_receiver(
                _log_stream, self._process.stdout, self._stdout, self._process.pid
            )
        if isinstance(self._stderr, Logger):
            self.start_receiver(
                _log_stream, self._process.stderr, self._stderr, self._process.pid
            )


async def _log_stream(
    stream: ByteReceiveStream, logger: logging.Logger, pid: int
) -> None:
    async for chunk in stream:
        try:
            text = chunk.decode("utf8")
            # Strip trailing line separators because `logger` adds one of
            # those as well.
            text = text.rstrip(os.linesep)
        except UnicodeDecodeError:
            text = "<Binary>"
        logger.info(text, extra={"subprocess": pid})
