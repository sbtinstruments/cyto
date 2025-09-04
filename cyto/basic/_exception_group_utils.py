from collections.abc import Iterable


# TODO: Use the "default" type argument when we get python 3.13:
#
#     BaseExceptionT_co: BaseException
#
def first_naked_exception[BaseExceptionT_co: BaseException](
    eg: BaseExceptionGroup[BaseExceptionT_co],
) -> BaseExceptionT_co:
    """Return the first naked (leaf) exception in the given group and subgroups.

    Assumes that there *is* such a naked exception. Does not work for
    `ExceptionGroup`s constructed manually to be empty.
    """
    return next(iter(naked_exceptions(eg)))


def naked_exceptions[BaseExceptionT_co: BaseException](
    eg: BaseExceptionGroup[BaseExceptionT_co],
) -> Iterable[BaseExceptionT_co]:
    """Yield each naked (leaf) exception in the given group and subgroups."""
    for exc in eg.exceptions:
        if isinstance(exc, ExceptionGroup | BaseExceptionGroup):
            yield from naked_exceptions(exc)
        else:
            yield exc
