# ruff: noqa: PLR2004
from __future__ import annotations

from typing import Annotated, Any, ClassVar, Literal, get_args

from pydantic import (
    ConfigDict,
    Field,
    RootModel,
    TypeAdapter,
    model_serializer,
    model_validator,
)

from ...model import FrozenModel

ValueType = Annotated[int | float | str, Field(union_mode="left_to_right")]

Finality = Literal["tentative", "final"]


def _tentative_item_json_schema(schema: dict[str, Any]) -> None:
    """Override the schema entirely."""
    schema.clear()
    schema.update(
        {
            "type": "object",
            # Anything that ends with "?"
            "patternProperties": {"^.*\\?$": TypeAdapter(ValueType).json_schema()},
            "minProperties": 1,
            "maxProperties": 1,
            "additionalProperties": False,
        }
    )


class TentativeItem(FrozenModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        json_schema_extra=_tentative_item_json_schema
    )

    finality: Finality = "tentative"  # Never serialized. Just for run-time distinction.
    key: str
    value: ValueType

    @model_validator(mode="before")
    @classmethod
    def _validate(cls, values: Any) -> dict[str, Any]:
        assert isinstance(values, dict)
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

    @model_serializer()
    def _serialize(self) -> dict[str, Any]:
        return {f"{self.key}?": self.value}


def _final_item_json_schema(schema: dict[str, Any]) -> None:
    """Override the schema entirely."""
    schema.clear()
    schema.update(
        {
            "type": "object",
            # Anything that does *not* end with "?"
            "patternProperties": {"^.*[^\\?]$": TypeAdapter(ValueType).json_schema()},
            "minProperties": 1,
            "maxProperties": 1,
            "additionalProperties": False,
        }
    )


class FinalItem(FrozenModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        json_schema_extra=_final_item_json_schema
    )

    finality: Finality = "final"  # Never serialized. Just for run-time distinction.
    key: str
    value: ValueType

    @model_validator(mode="before")
    @classmethod
    def _validate(cls, values: Any) -> dict[str, Any]:
        assert isinstance(values, dict)
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

    @model_serializer()
    def _serialize(self) -> dict[str, Any]:
        return {self.key: self.value}


def _subset_json_schema(schema: dict[str, Any]) -> None:
    """Override the schema."""
    schema.update(
        {
            "patternProperties": {
                # Both key and value *must* contain the delimiter.
                f"^.*{Subset.delimiter}.*$": {
                    "type": "string",
                    "pattern": f"^.*{Subset.delimiter}.*$",
                }
            },
            "minProperties": 1,
            "maxProperties": 1,
        }
    )
    schema.pop("required")
    schema.pop("properties")


class Subset(FrozenModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        json_schema_extra=_subset_json_schema
    )

    lhs: TentativeItem | FinalItem
    rhs: TentativeItem | FinalItem
    delimiter: ClassVar[str] = " ⊆ "

    @model_validator(mode="before")
    @classmethod
    def _validate(cls, values: Any) -> dict[str, Any]:
        assert isinstance(values, dict)
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

    @model_serializer()
    def _serialize(self) -> dict[str, Any]:
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


class TagToken(RootModel[str], frozen=True):
    root: Annotated[str, Field(strict=True, pattern=r"^\[[\w_\-]+\]$")]

    @property
    def name(self) -> str:
        assert isinstance(self.root, str)
        return self.root[1:-1]


class SectionBeginToken(RootModel[str], frozen=True):
    root: Annotated[str, Field(strict=True, pattern=r"^# [\w _\-]+$")]

    @property
    def name(self) -> str:
        assert isinstance(self.root, str)
        return self.root[2:]


# Order matters here!
#
# Pydantic tries each type in this union in sequence. It returns the first
# type that matches (read: the first value that we can coerce into the type).
# Therefore, it is important that, e.g., `TentativeItem` comes before
# `FinalItem` because the former is stricter than the latter. Otherwise,
# we would never get `TentativeItem` instances (because every value coerces
# to the lenient `FinalItem` type).
ItemToken = Subset | TentativeItem | FinalItem
SlideToken = ItemToken | str
SentinelToken = TagToken | SectionBeginToken
# Again, we put `SentinelToken` before `str` because the latter is the most
# lenient (all sentinels are strings).
#
# Note that the `dict`
#
# >    {"root": "[work-in-progress]"}
#
# has two possible interpretations in the `Token` union:
#
#  * `TagToken(root="[work-in-progress]")`
#  * `FinalItem(key="root", value="[work-in-progress]")`
#
# Therefore, it's important that `TagToken` comes before `FinalItem`.
_Token = SentinelToken | ItemToken | str
Token = Annotated[_Token, Field(union_mode="left_to_right")]
# Make sure that our types add up.
assert {*get_args(SlideToken), *get_args(SentinelToken)} == {*get_args(_Token)}


# TODO: Do we still need this?
RawSlide = dict[str, Any] | str
