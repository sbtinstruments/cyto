from datetime import UTC, datetime
from math import inf
from typing import Annotated

import portion
import pytest
from portion import CLOSED, OPEN
from portion.interval import Atomic
from pydantic import BaseModel, Field, ValidationError

from cyto.interval import (
    FloatInterval,
    FloatIntervalAdapter,
    IntInterval,
    IntIntervalAdapter,
    TimeIntervalAdapter,
)


def test_interval_adapter_validate() -> None:
    ### List of Atomics (named tuples)
    interval = IntIntervalAdapter.validate_python([Atomic(CLOSED, 1, 3, OPEN)])
    assert interval == portion.closedopen(1, 3)

    ### List of tuples
    interval = IntIntervalAdapter.validate_python([(CLOSED, 1, 3, OPEN)])
    assert interval == portion.closedopen(1, 3)

    interval = IntIntervalAdapter.validate_python(
        [(CLOSED, 1, 3, OPEN), (CLOSED, 2, 4, OPEN)]
    )
    assert interval == portion.closedopen(1, 4)

    with pytest.raises(ValidationError):
        IntIntervalAdapter.validate_python([1, 3])

    interval = IntIntervalAdapter.validate_python([])
    assert interval == portion.empty()

    ### String
    interval = IntIntervalAdapter.validate_python("[1, 3)")
    assert interval == portion.closedopen(1, 3)

    interval = IntIntervalAdapter.validate_python("[1, 3) | [2,4)")
    assert interval == portion.closedopen(1, 4)

    with pytest.raises(ValidationError):
        interval = IntIntervalAdapter.validate_python("<1, 3>")

    with pytest.raises(ValidationError):
        interval = IntIntervalAdapter.validate_python("[1; 3)")

    with pytest.raises(ValidationError):
        interval = IntIntervalAdapter.validate_python("")

    ### Dict
    interval = IntIntervalAdapter.validate_python(
        {"intervals": [Atomic(CLOSED, 1, 3, OPEN)]}
    )
    assert interval == portion.closedopen(1, 3)

    interval = IntIntervalAdapter.validate_python({})
    assert interval == portion.empty()

    with pytest.raises(ValidationError):
        IntIntervalAdapter.validate_python(
            {"intervals": [Atomic(CLOSED, 2.72, 3.14, OPEN)]}
        )

    with pytest.raises(ValidationError):
        IntIntervalAdapter.validate_python({"hi": "there"})

    ### Instance of portion.Interval
    interval = IntIntervalAdapter.validate_python(portion.closedopen(1, 3))
    assert interval == portion.closedopen(1, 3)

    interval = IntIntervalAdapter.validate_python(
        portion.closedopen(1, 3) | portion.closedopen(2, 4)
    )
    assert interval == portion.closedopen(1, 4)

    ### List of portion.Interval
    # TODO: Allow the user to use lists of `portion.Interval` directly.
    with pytest.raises(ValidationError):
        interval = IntIntervalAdapter.validate_python([portion.closedopen(1, 3)])

    ### Other types
    with pytest.raises(ValidationError):
        interval = IntIntervalAdapter.validate_python(3.14)


def test_interval_adapter_serialize() -> None:
    interval = IntIntervalAdapter.dump_python(portion.closedopen(1, 3))
    assert interval == [(True, 1, 3, False)]


def test_interval_in_model() -> None:
    class MyCriteria(BaseModel):
        interval_a: IntInterval = "(6, 8)"
        interval_b: IntInterval = [(CLOSED, 50, 60, CLOSED)]

    my_criteria = MyCriteria()
    assert my_criteria.interval_a == portion.open(6, 8)
    assert my_criteria.interval_b == portion.closed(50, 60)
    assert my_criteria.model_dump() == {
        "interval_a": [(False, 6, 8, False)],
        "interval_b": [(True, 50, 60, True)],
    }

    my_criteria = MyCriteria(interval_a="[7,10)", interval_b="[1,7)")
    assert my_criteria.interval_a == portion.closedopen(7, 10)
    assert my_criteria.interval_b == portion.closedopen(1, 7)
    assert my_criteria.model_dump() == {
        "interval_a": [(True, 7, 10, False)],
        "interval_b": [(True, 1, 7, False)],
    }


def test_type_strictness() -> None:
    ### Float where int is expected
    with pytest.raises(ValidationError):
        IntIntervalAdapter.validate_python([(CLOSED, 2.72, 3.14, OPEN)])
    with pytest.raises(ValidationError):
        IntIntervalAdapter.validate_python(portion.closedopen(2.72, 3.14))
    with pytest.raises(ValidationError):
        IntIntervalAdapter.validate_python("[2.72, 3.14)")

    ### Floats
    FloatIntervalAdapter.validate_python([(CLOSED, 2.72, 3.14, OPEN)])
    FloatIntervalAdapter.validate_python(portion.closedopen(2.72, 3.14))
    FloatIntervalAdapter.validate_python("[2.72, 3.14)")
    # An int is fine too (automatically coerced to float).
    FloatIntervalAdapter.validate_python("[2, 3.14)")

    ### Datetime
    interval = TimeIntervalAdapter.validate_python(
        [
            (
                CLOSED,
                datetime(1989, 1, 1, tzinfo=UTC),
                datetime(2000, 1, 1, tzinfo=UTC),
                OPEN,
            ),
            (
                CLOSED,
                datetime(1992, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 1, tzinfo=UTC),
                OPEN,
            ),
        ]
    )
    assert interval == portion.closedopen(
        datetime(1989, 1, 1, tzinfo=UTC), datetime(2024, 1, 1, tzinfo=UTC)
    )
    # Naive date (no timezone)
    interval = TimeIntervalAdapter.validate_python("[1989-05-28, 2024-12-01)")
    assert interval == portion.closedopen(datetime(1989, 5, 28), datetime(2024, 12, 1))  # noqa: DTZ001
    # Aware date (With timezone)
    interval = TimeIntervalAdapter.validate_python(
        "[1989-05-28T00:00Z, 2024-12-01T00:00Z)"
    )
    assert interval == portion.closedopen(
        datetime(1989, 5, 28, tzinfo=UTC), datetime(2024, 12, 1, tzinfo=UTC)
    )
    # Test with time
    interval = TimeIntervalAdapter.validate_python(
        "[1989-05-28T13:56:59.9876Z, 2024-12-01T00:01Z)"
    )
    assert interval == portion.closedopen(
        datetime(1989, 5, 28, 13, 56, 59, 987600, tzinfo=UTC),
        datetime(2024, 12, 1, 0, 1, tzinfo=UTC),
    )


def test_datetime_interval_with_inf() -> None:
    raw_interval = [[True, "2025-02-26T15:13:15.331522Z", inf, False]]
    interval = TimeIntervalAdapter.validate_python(raw_interval)
    assert interval == portion.closedopen(
        datetime(2025, 2, 26, 15, 13, 15, 331522, tzinfo=UTC),
        portion.inf,
    )

    # TODO: Can we make this serialize the upper bound as "inf"
    # instead of "null"?
    assert TimeIntervalAdapter.dump_json(interval) == (
        b'[[true,"2025-02-26T15:13:15.331522Z",null,false]]'
    )


def test_float_interval_field_with_int_default() -> None:
    class MyModel(BaseModel):
        bacteria_bounds: FloatInterval = portion.closedopen(0, 3.14)
        object_bounds: Annotated[
            FloatInterval,
            Field(default=portion.closedopen(1.5, 3)),
        ]

    my_model = MyModel()  # type: ignore[call-arg]

    assert isinstance(my_model.bacteria_bounds.lower, float)
    assert isinstance(my_model.bacteria_bounds.upper, float)
    assert my_model.bacteria_bounds.lower == 0
    assert my_model.bacteria_bounds.upper == 3.14  # noqa: PLR2004

    assert isinstance(my_model.object_bounds.lower, float)
    assert isinstance(my_model.object_bounds.upper, float)
    assert my_model.object_bounds.lower == 1.5  # noqa: PLR2004
    assert my_model.object_bounds.upper == 3  # noqa: PLR2004


def test_int_interval_field_with_float_default() -> None:
    class MyModel(BaseModel):
        my_interval: IntInterval = portion.closedopen(-3, 2.72)

    with pytest.raises(
        ValidationError,
        match="Input should be a valid integer, got a number with a fractional part",
    ):
        MyModel()


def test_int_interval_field_with_strings() -> None:
    # Bogus values: "A", "B"
    class MyModelAB(BaseModel):
        my_interval: IntInterval = portion.closedopen("A", "B")

    with pytest.raises(
        ValidationError,
        match="Input should be a valid integer, unable to parse string as an integer",
    ):
        MyModelAB()

    # Bogus values: "B", "A"
    class MyModelBA(BaseModel):
        my_interval: IntInterval = portion.closedopen("B", "A")

    # Surprisingly, we can actually create an instance!
    # This is because portion determines that the interval is actually
    # empty. E.g., assume that B=1 and A=0, then the interval [1,0) is
    # of size zero. I (FPA) guess that this is a feature and not a bug.
    my_model_ba = MyModelBA()
    assert my_model_ba.my_interval == portion.empty()

    # Good values: "1", "2"
    class MyModel12(BaseModel):
        my_interval: IntInterval = portion.closedopen("1", "2")

    my_model_12 = MyModel12()
    assert isinstance(my_model_12.my_interval.lower, int)
    assert isinstance(my_model_12.my_interval.upper, int)
    assert my_model_12.my_interval.lower == 1
    assert my_model_12.my_interval.upper == 2  # noqa: PLR2004

    # Bad values: "3.14", "5"
    class MyModelPi5(BaseModel):
        my_interval: IntInterval = portion.closedopen("3.14", "5")

    with pytest.raises(
        ValidationError,
        match="Input should be a valid integer, unable to parse string as an integer",
    ):
        MyModelPi5()
