from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Annotated, Any

import portion
import portion.interval
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    GetPydanticSchema,
    TypeAdapter,
    ValidatorFunctionWrapHandler,
    model_serializer,
    model_validator,
)

Conv = Callable[[Any], Any]


def _create_io_annotation(
    *, type_: type, conv: Conv | None = None
) -> GetPydanticSchema:
    if conv is None:
        conv = _create_conv(type_)

    class IntervalAnnotation(BaseModel):
        model_config = ConfigDict(frozen=True, extra="forbid")

        intervals: tuple[portion.interval.Atomic, ...] = ()

        @model_validator(mode="wrap")
        @classmethod
        def _validate(
            cls, data: Any, handler: ValidatorFunctionWrapHandler
        ) -> portion.Interval:
            # Early out if there is nothing to do
            if isinstance(data, portion.Interval):
                # Normally, we would just return `data` directly since it's already
                # of the right type and be done with it. However, since
                # `portion.Interval` does not type-check at all, we want to apply a
                # little more due diligence on top. E.g., to catch cases like this:
                #
                #     IntIntervalAdapter.validate_python(portion.closedopen(2.72, 3.14))
                #
                # Note how we use `float`s together with `IntInterval`. That's a no-go.
                #
                # There are many ways to implement this check. For now, we simply
                # convert `data` back into a raw list of tuples (using
                # `portion.to_data`). In turn, the validation logic below takes care
                # of the rest (specifically, the `if isinstance(data, Iterable)` part).
                data = portion.to_data(data)

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

    # This is a fancy way to say: Hey pydantic, ignore other type information
    # and treat it like `IntervalAnnotation`.
    #
    # In essence, `GetPydanticSchema` is like a type override. E.g., in this annotation:
    #
    #     my_field: Annotated[int, GetPydanticSchema(lambda _s, handler: handler(str))]
    #
    # we have `_s=int`, and we tell pydantic to ignore `_s` and use `str` instead.
    # In Pydantic's view, `my_field` is a `str` and it validates/serializes it as such.
    return GetPydanticSchema(lambda _source_type, handler: handler(IntervalAnnotation))


def _create_conv(type_: type) -> Conv:
    type_adapter = TypeAdapter(type_)  # type: ignore[var-annotated]

    def _validate(value: Any) -> type_:  # type: ignore[valid-type]
        if isinstance(value, str):
            return type_adapter.validate_strings(value)  # type: ignore[no-any-return]
        return type_adapter.validate_python(value)  # type: ignore[no-any-return]

    _validate.__name__ = f"_validate_{type_.__name__}"

    return _validate


def _create_interval_annotation(type_: type, conv: Conv | None = None) -> Any:
    # Provides validator and serializer
    yield _create_io_annotation(type_=type_, conv=conv)
    # Allows us to specify default values using, e.g., strings. Example:
    #
    #     class MyCriteria(BaseModel):
    #         interval_a: IntInterval = "(6, 8)"
    #         interval_b: IntInterval = [(CLOSED, 50, 60, CLOSED)]
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
