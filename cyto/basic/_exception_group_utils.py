from collections.abc import Iterable
from typing import TypeVar

_BaseExceptionT_co = TypeVar(
    "_BaseExceptionT_co",
    bound=BaseException,
    covariant=True,
    # TODO: Use the "default" argument when we get python 3.13
    # default=BaseException
)


def first_naked_exception(
    eg: BaseExceptionGroup[_BaseExceptionT_co],
) -> _BaseExceptionT_co:
    """Return the first naked (leaf) exception in the given group and subgroups.

    Assumes that there *is* such a naked exception. Does not work for
    `ExceptionGroup`s constructed manually to be empty.
    """
    return next(iter(naked_exceptions(eg)))


def naked_exceptions(
    eg: BaseExceptionGroup[_BaseExceptionT_co],
) -> Iterable[_BaseExceptionT_co]:
    """Yield each naked (leaf) exception in the given group and subgroups."""
    for exc in eg.exceptions:
        if isinstance(exc, ExceptionGroup | BaseExceptionGroup):
            yield from naked_exceptions(exc)
        else:
            yield exc
