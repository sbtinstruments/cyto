from __future__ import annotations

from typing import Any, Callable, Generic, Iterator, TypeVar

import portion
from portion import Interval as PortionInterval

T = TypeVar("T")


# TODO: Check if portion added type hints since then.
# See: https://github.com/AlexandreDecan/portion/issues/27
class Interval(Generic[T], PortionInterval):  # type: ignore[misc]
    @classmethod
    def closedopen(cls, lower: T, upper: T | portion.inf | None = None) -> Interval[T]:
        if upper is None:
            upper = portion.inf
        return cls(portion.closedopen(lower, upper))

    @classmethod
    def __get_validators__(
        cls,
    ) -> Iterator[Callable[[Any], Interval[T]]]:
        yield cls.validate_type

    @classmethod
    def validate_type(cls, val: Any) -> Interval[T]:
        if isinstance(val, cls):
            return val
        return cls(portion.closedopen(*val))
