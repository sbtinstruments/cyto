from itertools import tee
from typing import Iterable, Iterator, TypeVar

T = TypeVar("T")


# TODO: Replace with `itertools.pairwise` when we get Python 3.10
# Current implementation is from:
# https://docs.python.org/3/library/itertools.html#itertools.pairwise
def pairwise(iterable: Iterable[T]) -> Iterator[tuple[T, T]]:
    """Pair up an iterable: 'ABCDEFG' --> AB BC CD DE EF FG."""
    a, b = tee(iterable)  # pylint: disable=invalid-name
    next(b, None)
    return zip(a, b)
