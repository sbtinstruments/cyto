from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Annotated, Any

import portion
import portion.interval
from pydantic import (
    BaseModel,
    Field,
    TypeAdapter,
    ValidatorFunctionWrapHandler,
    model_serializer,
    model_validator,
)

Conv = Callable[[Any], Any]


def _create_io_annotation(*, type_: type, conv: Conv | None = None) -> type[BaseModel]:  # noqa: C901
    if conv is None:
        conv = _create_conv(type_)

    def _validate_portion_interval(interval: portion.Interval) -> portion.Interval:
        for atomic in interval._intervals:  # noqa: SLF001
            assert isinstance(atomic, portion.interval.Atomic)
            assert isinstance(atomic.lower, type_)
            assert isinstance(atomic.upper, type_)
        return interval

    class IntervalAnnotation(BaseModel, frozen=True, extra="forbid"):
        intervals: tuple[portion.interval.Atomic, ...] = ()

        @model_validator(mode="wrap")
        @classmethod
        def _validate(
            cls, data: Any, handler: ValidatorFunctionWrapHandler
        ) -> portion.Interval:
            # Early out if there is nothing to do
            if isinstance(data, portion.Interval):
                # Normally, we would just return `data` directly and be done with it.
                # However, since `portion.Interval` does not type-check at all, we want
                # to apply a little more due diligence on top via
                # `_validate_portion_interval`. E.g., to catch cases like this:
                #
                #     IntIntervalAdapter.validate_python(portion.closedopen(2.72, 3.14))
                #
                # Note how we use `float`s together with `IntInterval`. That's a no-go.
                return _validate_portion_interval(data)

            # If we get a dict, we let the normal pydantic logic (e.g., `handler`)
            # take care of it.
            if isinstance(data, dict):
                # Note that `handler` applies the usual validation:
                #
                #  * `mode="before"` validators
                #  * Pydantic-provided validators
                #  * `mode="after"` validators
                #
                validated = handler(data)
                assert isinstance(validated, cls)
                return portion.from_data(validated.intervals, conv=conv)

            if isinstance(data, str):
                return portion.from_string(data, conv=conv)

            if isinstance(data, Iterable):
                try:
                    return portion.from_data(data, conv=conv)
                # ruff: noqa: ERA001
                #
                # TypeError: If data contains an item that we can not unpack into
                # four elements. Inside `portion.from_data`, we have this:
                #
                #     for item in data:
                #         left, lower, upper, right = item
                #         ...
                #
                # So if item is not, e.g., a 4-tuple, then we get a TypeError.
                except TypeError as exc:
                    raise ValueError(
                        f"Could not parse '{data}' a portion.Interval. "
                        "Make sure that all items are in the shape of "
                        "(left,lower,upper,right)"
                    ) from exc

            raise ValueError(f"Can not parse '{data}' into a portion.Interval")

        @model_serializer(mode="plain")
        def _serialize(self: portion.Interval) -> list[portion.interval.Atomic]:
            result = portion.to_data(self)
            assert isinstance(result, list)
            return result

    return IntervalAnnotation


def _create_conv(type_: type) -> Conv:
    type_adapter = TypeAdapter(type_)  # type: ignore[var-annotated]

    def _validate(value: Any) -> type_:  # type: ignore[valid-type]
        if isinstance(value, str):
            return type_adapter.validate_strings(value)  # type: ignore[no-any-return]
        return type_adapter.validate_python(value)  # type: ignore[no-any-return]

    _validate.__name__ = f"_validate_{type_.__name__}"

    return _validate


def _create_interval_annotation(type_: type) -> Any:
    # Provides validator and serializer
    yield _create_io_annotation(type_=type_)
    # Allows us to specify default values using, e.g., strings. Example:
    #
    #     class MyCriteria(BaseModel):
    #         good: IntInterval = "(6, 8)"
    #         bad: IntInterval = [(CLOSED, 50, 60, CLOSED)]
    #
    yield Field(validate_default=True)


# Ideally, we would just do:
#
#     IntInterval = create_interval_annotation(int)
#
# Unfortunately, the current generation of compile-time type checkers do not support
# this dynamic approach yet.
IntInterval = Annotated[portion.Interval, *_create_interval_annotation(int)]
IntIntervalAdapter = TypeAdapter(IntInterval)

FloatInterval = Annotated[portion.Interval, *_create_interval_annotation(float)]
FloatIntervalAdapter = TypeAdapter(FloatInterval)

TimeInterval = Annotated[portion.Interval, *_create_interval_annotation(datetime)]
TimeIntervalAdapter = TypeAdapter(TimeInterval)
