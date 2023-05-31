from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from typing import Any, ClassVar, Literal, get_args, overload

from pydantic import StrictFloat, StrictInt, parse_obj_as, root_validator

from ...model import FrozenModel

ValueType = StrictInt | StrictFloat | str

Finality = Literal["tentative", "final"]


class TentativeItem(FrozenModel):
    finality: Finality = "tentative"  # Never serialized. Just for run-time distinction.
    key: str
    value: ValueType

    @root_validator(pre=True)
    def _validate(cls, values: dict[str, Any]) -> dict[str, Any]:
        # Early out if we get each field directly
        if "key" in values and "value" in values:
            assert values.get("finality") in (None, "tentative")
            return values
        # Otherwise, we parse the raw dict
        key, value = _exactly_one_item(values)
        assert key.endswith("?")
        return {
            "finality": "tentative",
            "key": key[:-1],
            "value": value,
        }

    # A003: We have to use `dict` since pydantic choose this name.
    def dict(self, **_kwargs: Any) -> dict[str, Any]:  # noqa: A003
        return {f"{self.key}?": self.value}


class FinalItem(FrozenModel):
    finality: Finality = "final"  # Never serialized. Just for run-time distinction.
    key: str
    value: ValueType

    @root_validator(pre=True)
    def _validate(cls, values: dict[str, Any]) -> dict[str, Any]:
        # Early out if we get each field directly
        if "key" in values and "value" in values:
            assert values.get("finality") in (None, "final")
            return values
        # Otherwise, we parse the raw dict
        key, value = _exactly_one_item(values)
        return {
            "finality": "final",
            "key": key,
            "value": value,
        }

    # A003: We have to use `dict` since pydantic choose this name.
    def dict(self, **_kwargs: Any) -> dict[str, Any]:  # noqa: A003
        return {self.key: self.value}


class Subset(FrozenModel):
    lhs: TentativeItem | FinalItem
    rhs: TentativeItem | FinalItem
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

    # A003: We have to use `dict` since pydantic choose this name.
    def dict(self, **_kwargs: Any) -> dict[str, Any]:  # noqa: A003
        lhs_suffix = "?" if isinstance(self.lhs, TentativeItem) else ""
        rhs_suffix = "?" if isinstance(self.rhs, TentativeItem) else ""
        key = f"{self.lhs.key}{lhs_suffix}{self.delimiter}{self.rhs.key}{rhs_suffix}"
        value = f"{self.lhs.value}{self.delimiter}{self.rhs.value}"
        return {key: value}

    @property
    def finality(self) -> Finality:
        if self.lhs.finality == "tentative" or self.rhs.finality == "tentative":
            return "tentative"
        return "final"


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


# Use this sentinel to indicate that the keynote is tentative (even though
# it only contains "final" content). E.g., to denote that the you'll add
# additional slides later.
Tentative = Literal["TENTATIVE"]


# Order matters here!
#
# Pydantic tries each type in this union in sequence. It returns the first
# type that matches (read: the first value that we can coerce into the type).
# Therefore, it is important that, e.g., `TentativeItem` comes before
# `FinalItem` because the former is stricter than the latter. Otherwise,
# we would never get `TentativeItem` instances (because every value coerces
# to the lenient `FinalItem` type).
ContentSlide = Subset | TentativeItem | FinalItem
SentinelSlide = Tentative
Slide = ContentSlide | SentinelSlide


RawSlide = dict[str, Any] | Tentative


class Keynote(FrozenModel, Sequence[Slide]):
    """Sequence of keynote slides.

    Serializes to something like this:

        [
            { "intact cells/ml ⊆ total particles/ml": "12 000 ⊆ 50 000" },
            { "flow_rate?": 32.1 },
            { "ID": "A03" },
            "TENTATIVE"
        ]

    """

    __root__: tuple[Slide, ...] = ()

    @overload
    def __getitem__(self, item: int) -> Slide:
        ...

    @overload
    def __getitem__(self, _slice: slice) -> Sequence[Slide]:
        ...

    def __getitem__(self, item: Any) -> Any:
        return self.__root__[item]

    # TODO: Use the `override` decorator when we get python 3.12
    def __iter__(self) -> Iterator[Slide]:  # type: ignore[override]
        return iter(self.__root__)

    def __len__(self) -> int:
        return len(self.__root__)

    def __add__(self, rhs: Any) -> Keynote:
        """Return a copy with the given slide appended.

        Returns a copy. Does *not* mutate this instance.
        """
        slide = parse_obj_as(Slide, rhs)  # type: ignore[var-annotated, arg-type]
        return Keynote(__root__=(*self.__root__, slide))

    @property
    def finality(self) -> Finality:
        """Return True if all content is final and there is no "TENTATIVE" slide.

        Otherwise, return "tentative".

        Note that an empty keynote is still "final".
        """
        all_content_is_final = all(
            slide.finality == "final" for slide in self.content()
        )
        no_tentative_sentinel = "TENTATIVE" not in self
        if all_content_is_final and no_tentative_sentinel:
            return "final"
        return "tentative"

    def content(self) -> Iterable[ContentSlide]:
        """Return all content slides (e.g., no sentinel slides like "TENTATIVE")."""
        return (
            slide  # type: ignore[misc]
            for slide in self
            if isinstance(slide, get_args(ContentSlide))
        )

    def final_content(self) -> Iterable[ContentSlide]:
        """Return all "final" content slides (i.e., non-tentative slides)."""
        return (slide for slide in self.content() if slide.finality == "final")
