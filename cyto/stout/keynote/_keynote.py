from __future__ import annotations

from collections.abc import Sequence
from typing import Any, ClassVar, Iterator

from pydantic import parse_obj_as, root_validator

from ...model import FrozenModel

# Order matters here!
#
# Pydantic happily coerces `32.1` to an `int`. Therefore, we place
# `float` before `int` here.
ValueType = float | int | str


class TentativeItem(FrozenModel):
    key: str
    value: ValueType

    @root_validator(pre=True)
    def _validate(cls, values: dict[str, Any]) -> dict[str, Any]:
        # Early out if we get each field directly
        if "key" in values and "value" in values:
            return values
        # Otherwise, we parse the raw dict
        key, value = _exactly_one_item(values)
        assert key.endswith("?")
        return {
            "key": key[:-1],
            "value": value,
        }

    def dict(self, **kwargs: Any) -> dict[str, Any]:
        return {f"{self.key}?": self.value}


class Item(FrozenModel):
    key: str
    value: ValueType

    @root_validator(pre=True)
    def _validate(cls, values: dict[str, Any]) -> dict[str, Any]:
        # Early out if we get each field directly
        if "key" in values and "value" in values:
            return values
        # Otherwise, we parse the raw dict
        key, value = _exactly_one_item(values)
        return {
            "key": key,
            "value": value,
        }

    def dict(self, **kwargs: Any) -> dict[str, Any]:
        return {self.key: self.value}


class Subset(FrozenModel):
    lhs: Item
    rhs: Item
    delimiter: ClassVar[str] = " ⊆ "

    @root_validator(pre=True)
    def _validate(cls, values: dict[str, Any]) -> dict[str, Any]:
        # Early out if we get each field directly
        if "lhs" in values and "rhs" in values:
            return values
        # Otherwise, we parse the raw dict
        key, value = _exactly_one_item(values)
        assert isinstance(value, str)
        key_operands = key.split(cls.delimiter)
        value_operands = value.split(cls.delimiter)
        assert len(key_operands) == 2
        assert len(value_operands) == 2
        return {
            "lhs": {key_operands[0]: value_operands[0]},
            "rhs": {key_operands[1]: value_operands[1]},
        }

    def dict(self, **kwargs: Any) -> dict[str, Any]:
        key = f"{self.lhs.key}{self.delimiter}{self.rhs.key}"
        value = f"{self.lhs.value}{self.delimiter}{self.rhs.value}"
        return {key: value}


def _exactly_one_item(values: dict[str, Any]) -> tuple[str, Any]:
    items = iter(values.items())
    try:
        key, value = next(items)
    except StopIteration as exc:
        raise ValueError("There must be at least one item in values") from exc
    try:
        next(items)
    except StopIteration:
        return key, value
    raise ValueError("There must not be more than one item in values")


# Order matters here!
#
# Pydantic tries each type in this union in sequence. It returns the first
# type that matches (read: the first value that we can coerce into the type).
# Therefore, it is important that, e.g., `TentativeValue` comes before `Value`
# because the former is stricter than the latter. Otherwise, we would never
# get `TentativeValue` instances (because every value coerces to the lenient
# `Value` type).
KeynoteSlide = Subset | TentativeItem | Item


class Keynote(FrozenModel, Sequence[KeynoteSlide]):
    """Sequence of keynote slides.

    Serializes to something like this:

        [
            { "intact cells/ml ⊆ total particles/ml": "12 000 ⊆ 50 000" },
            { "flow_rate?": 32.1 },
            { "ID": "A03" }
        ]

    """

    __root__: tuple[KeynoteSlide, ...] = tuple()

    def __getitem__(self, item: int) -> KeynoteSlide:
        return self.__root__[item]

    def __iter__(self) -> Iterator[KeynoteSlide]:
        return iter(self.__root__)

    def __len__(self) -> int:
        return len(self.__root__)

    def __add__(self, rhs: Any) -> Keynote:
        """Return a copy with the given slide appended.

        Returns a copy. Does *not* mutate this instance.
        """
        slide = parse_obj_as(KeynoteSlide, rhs)
        return Keynote(__root__=self.__root__ + (slide,))

    def is_final(self) -> bool:
        """Contains purely non-tentative items and at least one such item."""
        return bool(self) and not any(
            isinstance(slide, TentativeItem) for slide in self
        )
