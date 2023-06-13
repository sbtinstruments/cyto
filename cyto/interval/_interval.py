from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any, Generic, TypeVar

import portion
from portion import Interval as PortionInterval
from portion.io import from_string as portion_from_string
from pydantic.json import ENCODERS_BY_TYPE

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
        if isinstance(val, str):
            # TODO: Unite the `conv=float` type with the template type (`T`)
            return cls(portion_from_string(val, conv=float))
        return cls(portion.closedopen(*val))


ENCODERS_BY_TYPE[Interval] = str
