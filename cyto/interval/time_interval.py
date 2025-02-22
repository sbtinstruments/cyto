# Inspired by `portion`'s API but with types
from datetime import datetime, timedelta
from typing import Self, overload

from pydantic import model_validator

from ..model import FrozenModel

__all__ = ["ClosedOpen", "ClosedOpenFin", "ClosedOpenInf", "closed_open"]


class ClosedOpenInf(FrozenModel):
    lower: datetime


class ClosedOpenFin(FrozenModel):
    lower: datetime
    upper: datetime

    @model_validator(mode="after")
    def _lower_before_upper(self) -> Self:
        if self.lower > self.upper:
            raise ValueError('"lower" must come before "upper"')
        return self

    def duration(self) -> timedelta:
        """Return the time between lower and upper."""
        return self.upper - self.lower

    def __contains__(self, value: datetime) -> bool:
        return self.lower <= value < self.upper


ClosedOpen = ClosedOpenInf | ClosedOpenFin


@overload
def closed_open(lower: datetime, upper: None = None) -> ClosedOpenInf: ...


@overload
def closed_open(lower: datetime, upper: datetime) -> ClosedOpenFin: ...


def closed_open(lower: datetime, upper: datetime | None = None) -> ClosedOpen:
    if upper is None:
        return ClosedOpenInf(lower=lower)
    return ClosedOpenFin(lower=lower, upper=upper)
