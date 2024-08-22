from datetime import UTC, datetime

import portion
import pytest
from portion import CLOSED, OPEN
from portion.interval import Atomic
from pydantic import BaseModel, ValidationError

from cyto.interval import (
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
        good: IntInterval = "(6, 8)"
        bad: IntInterval = [(CLOSED, 50, 60, CLOSED)]

    my_criteria = MyCriteria()
    assert my_criteria.good == portion.open(6, 8)
    assert my_criteria.bad == portion.closed(50, 60)
    assert my_criteria.model_dump() == {
        "good": [(False, 6, 8, False)],
        "bad": [(True, 50, 60, True)],
    }

    my_criteria = MyCriteria(good="[7,10)", bad="[1,7)")
    assert my_criteria.good == portion.closedopen(7, 10)
    assert my_criteria.bad == portion.closedopen(1, 7)
    assert my_criteria.model_dump() == {
        "good": [(True, 7, 10, False)],
        "bad": [(True, 1, 7, False)],
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
