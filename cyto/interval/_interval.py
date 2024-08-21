from __future__ import annotations

from typing import Any, Generic, TypeVar

import portion
from portion import Interval as PortionInterval
from portion.const import _PInf
from portion.io import from_string as portion_from_string
from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

__all__ = ["Interval"]

T = TypeVar("T")


# TODO: Check if portion added type hints since then.
# See: https://github.com/AlexandreDecan/portion/issues/27
class Interval(PortionInterval, Generic[T]):  # type: ignore[misc]
    @classmethod
    def closed(cls, lower: T, upper: T) -> Interval[T]:
        return cls(portion.closed(lower, upper))

    @classmethod
    def closedopen(cls, lower: T, upper: T | _PInf | None = None) -> Interval[T]:
        if upper is None:
            upper = portion.inf
        return cls(portion.closedopen(lower, upper))

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_plain_validator_function(cls.validate_type)

    @classmethod
    def validate_type(cls, val: Any) -> Interval:
        if isinstance(val, cls):
            return val
        if isinstance(val, str):
            # TODO: Unite the `conv=float` type with the template type (`T`)
            return cls(portion_from_string(val, conv=float))
        return cls(portion.closedopen(*val))
