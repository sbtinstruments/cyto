# Inspired by `portion`'s API but with types
from datetime import datetime, timedelta
from typing import Any, overload

from pydantic import root_validator

from ..model import FrozenModel

__all__ = ["ClosedOpenInf", "ClosedOpenFin", "ClosedOpen", "closed_open"]


class ClosedOpenInf(FrozenModel):
    lower: datetime


class ClosedOpenFin(FrozenModel):
    lower: datetime
    upper: datetime

    @root_validator
    def _lower_before_upper(cls, values: dict[str, Any]) -> dict[str, Any]:
        lower, upper = values.get("lower"), values.get("upper")
        assert isinstance(lower, datetime)
        assert isinstance(upper, datetime)
        if lower > upper:
            raise ValueError('"lower" must come before "upper"')
        return values

    def duration(self) -> timedelta:
        """Return the time between lower and upper."""
        return self.upper - self.lower

    def __contains__(self, value: datetime) -> bool:
        return self.lower <= value < self.upper


ClosedOpen = ClosedOpenInf | ClosedOpenFin


@overload
def closed_open(lower: datetime, upper: None = None) -> ClosedOpenInf:
    ...


@overload
def closed_open(lower: datetime, upper: datetime) -> ClosedOpenFin:
    ...


def closed_open(lower: datetime, upper: datetime | None = None) -> ClosedOpen:
    if upper is None:
        return ClosedOpenInf(lower=lower)
    return ClosedOpenFin(lower=lower, upper=upper)
