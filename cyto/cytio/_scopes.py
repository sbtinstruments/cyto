"""Time-based, structured flow control.

## Overview

### `anyio.fail_after` (aka "raise if slower")
If the wrapped code is slower than the time limit, we cancel said code and
raise `TimeoutError`.
If the wrapped code is faster than the time limit, we do nothing.

### `anyio.move_on_after` (aka "cancel if slower")
If the wrapped code is slower than the time limit, we cancel said code.
If the wrapped code is faster than the time limit, we do nothing.

### `wait_exactly` (aka "cancel if slower, wait if faster")
If the wrapped code is slower than the time limit, we cancel said code.
If the wrapped code is faster than the time limit, we wait until the time limit.

### `wait_if_faster`
If the wrapped code is slower than the time limit, we wait until said code is done.
If the wrapped code is faster than the time limit, we wait until the time limit.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager, contextmanager
from datetime import timedelta
from typing import AsyncIterator, Callable, Iterator, Union

import anyio

TimeFunc = Callable[[], Union[timedelta, None]]


@contextmanager
def warn_after(
    time_limit: Union[float, timedelta, None, TimeFunc], *, logger: logging.Logger
) -> Iterator[None]:
    begin_at = anyio.current_time()
    try:
        yield
    finally:
        end_at = anyio.current_time()
        elapsed = end_at - begin_at
        if callable(time_limit):
            time_limit = time_limit()
        if time_limit is not None:
            if isinstance(time_limit, timedelta):
                time_limit = time_limit.total_seconds()
            if elapsed >= time_limit:
                delta = elapsed - time_limit
                logger.warning(f"Exceeded the time limit with {delta:0.2f} seconds")


@asynccontextmanager
async def wait_exactly(
    time_limit: Union[float, timedelta], shield: bool = False
) -> AsyncIterator[None]:
    """Run for exactly `time_limit` seconds.

    If the wrapped code is slower than `time_limit`, we cancel said code.
    If the wrapped code is faster than `time_limit`, we wait until the time limit.
    """
    if isinstance(time_limit, timedelta):
        time_limit = time_limit.total_seconds()
    with anyio.move_on_after(time_limit, shield=shield):
        yield
        await anyio.sleep_forever()


@asynccontextmanager
async def wait_if_faster(time_limit: Union[float, timedelta]) -> AsyncIterator[None]:
    """Run for at least `time_limit` seconds.

    If the wrapped code is slower than `time_limit`, we wait until said code is done.
    If the wrapped code is faster than `time_limit`, we wait until the time limit.
    """
    if isinstance(time_limit, timedelta):
        time_limit = time_limit.total_seconds()
    begin_at = anyio.current_time()
    end_at = begin_at + time_limit
    yield
    await anyio.sleep_until(end_at)
