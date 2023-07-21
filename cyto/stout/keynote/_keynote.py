from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from typing import Any, ClassVar, Literal, get_args, overload

from pydantic import StrictFloat, StrictInt, parse_obj_as, root_validator, schema_of

from ...model import FrozenModel

ValueType = StrictInt | StrictFloat | str

Finality = Literal["tentative", "final"]
FinalityFilter = Literal["only-final", "only-tentative", "include-all"]


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

    class Config:
        @staticmethod
        def schema_extra(schema: dict[str, Any]) -> None:
            """Override the schema entirely."""
            schema.clear()
            schema.update(
                {
                    "type": "object",
                    # Anything that ends with "?"
                    "patternProperties": {
                        "^.*\\?$": schema_of(ValueType, title="Value")
                    },
                    "minProperties": 1,
                    "maxProperties": 1,
                    "additionalProperties": False,
                }
            )


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

    class Config:
        @staticmethod
        def schema_extra(schema: dict[str, Any]) -> None:
            """Override the schema entirely."""
            schema.clear()
            schema.update(
                {
                    "type": "object",
                    # Anything that does *not* end with "?"
                    "patternProperties": {
                        "^.*[^\\?]$": schema_of(ValueType, title="Value")
                    },
                    "minProperties": 1,
                    "maxProperties": 1,
                    "additionalProperties": False,
                }
            )


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

    class Config:
        @staticmethod
        def schema_extra(schema: dict[str, Any]) -> None:
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
#
# MUST be the first slide.
# MUST be unique (there can not be multiple "TENTATIVE" slides).
Tentative = Literal["TENTATIVE"]
# Use this sentinel to indicate the the subsequent slides are nonessential.
# E.g., said slides represent additional information, deep dives, reference
# material, etc.
#
# MUST be unique (there can not be multiple "TENTATIVE" slides).
BonusSlides = Literal["BONUS SLIDES"]
BonusSlidesFilter = Literal["exclude", "include", "only"]

# Order matters here!
#
# Pydantic tries each type in this union in sequence. It returns the first
# type that matches (read: the first value that we can coerce into the type).
# Therefore, it is important that, e.g., `TentativeItem` comes before
# `FinalItem` because the former is stricter than the latter. Otherwise,
# we would never get `TentativeItem` instances (because every value coerces
# to the lenient `FinalItem` type).
ItemSlide = Subset | TentativeItem | FinalItem
ContentSlide = ItemSlide | str
SentinelSlide = Tentative | BonusSlides
# Again, we put `SentinelSlide` before `str` because the latter is the most
# lenient (all sentinels are strings).
Slide = ItemSlide | SentinelSlide | str
# Make sure that our types add up.
assert {*get_args(ContentSlide), *get_args(SentinelSlide)} == {*get_args(Slide)}


RawSlide = dict[str, Any] | Tentative


class Keynote(FrozenModel, Sequence[Slide]):
    """Sequence of keynote slides.

    Serializes to something like this:

        [
            "TENTATIVE",
            { "intact cells/ml ⊆ total particles/ml": "12 000 ⊆ 50 000" },
            { "flow_rate?": 32.1 },
            { "ID": "A03" }
        ]

    """

    __root__: tuple[Slide, ...] = ()

    @root_validator()
    def _validate_sentinels(cls, values: dict[str, Any]) -> dict[str, Any]:
        root = values["__root__"]
        # "TENTATIVE" sentinel MUST be the first slide
        if "TENTATIVE" in root and root[0] != "TENTATIVE":
            raise ValueError("The 'TENTATIVE' slide must be the first slide")
        # "TENTATIVE" sentinel MUST be unique
        if len([slide for slide in root if slide == "TENTATIVE"]) > 1:
            raise ValueError("There can only be one 'TENTATIVE' slide")
        # "BONUS SLIDES" sentinel MUST be unique
        if len([slide for slide in root if slide == "BONUS SLIDES"]) > 1:
            raise ValueError("There can only be one 'BONUS SLIDES' slide")
        return values

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
        if isinstance(rhs, Iterable):
            return Keynote(__root__=(*self.__root__, *rhs))
        slide = parse_obj_as(Slide, rhs)  # type: ignore[var-annotated, arg-type]
        return Keynote(__root__=(*self.__root__, slide))

    @property
    def finality(self) -> Finality:
        """Return "tentative" if there is any tentative content.

        Otherwise, return "final".

        Note that:

         * The empty keynote is "final".
         * A keynote with a single "TENTATIVE" slide is "tentative".
         * Slides after the "BONUS SLIDES" sentinel do not count.

        """
        tentative_content = (
            True
            for _ in self.content(bonus_slides="exclude", finality="only-tentative")
        )
        tentative_sentinel = "TENTATIVE" in self
        if any(tentative_content) or tentative_sentinel:
            return "tentative"
        return "final"

    def content(
        self,
        *,
        bonus_slides: BonusSlidesFilter | None = None,
        finality: FinalityFilter | None = None,
    ) -> Iterable[ContentSlide]:
        """Return all content slides (e.g., no sentinel slides like "TENTATIVE").

        This is the primary keynote "view". You usually interact via the keynote
        through this function. This view takes the sentinels ("TENTATIVE",
        "BONUS SLIDES") into account and allows you to filter on it.


        ## Analogy to computer language theory

        It might be useful to draw analogy to computer language theory:

         * Source code: List of raw slides (e.g., `["Welcome", {"ID?": "A03"}]`)
         * Lexer: The `Keynote.parse_obj` that we get from pydantic
         * Tokens: A `Keynote` instance (tuple of `Slide`s)
         * Parser: The `Keynote.content` function
         * Abstract syntax tree (AST): An iterable of `ContentSlide`

        These concepts connect like this:

            Source code --(lexer)--> Tokens --(parser)--> AST

        In this analogy, the `Keynote` itself is just a sequence of tokens. Not
        very meaningful on their own; more like an intermediate calculation.
        After we call `Keynote.content`, we get the AST. We can use the AST
        directly.

        Note that this analogy does not hold up completely since
        `Keynote._validate_sentinels` goes beyond the scope of what a lexer
        would do.

        ## Default values

        Note that this function:

         * Excludes bonus slides per default.
           Use `bonus_filter` to override this.
         * Includes both tentative and final slides per default.
           Use `finality_filter` to override this.

        """
        if bonus_slides is None:
            bonus_slides = "exclude"
        if finality is None:
            finality = "include-all"

        reached_tentative_sentinel = False
        reached_bonus_slides_sentinel = False

        for slide in self:
            match slide:
                case "TENTATIVE":
                    reached_tentative_sentinel = True
                case "BONUS SLIDES":
                    reached_bonus_slides_sentinel = True

            # Only final slides: Stop when we reach the "TENTATIVE" sentinel.
            # Since the "TENTATIVE" sentinel MUST come first, this means that we
            # early out right away.
            if reached_tentative_sentinel and finality == "only-final":
                return

            match bonus_slides:
                # Exclude bonus slides: Stop when we reach the "BONUS SLIDES" sentinel
                case "exclude" if reached_bonus_slides_sentinel:
                    return
                # Only bonus slides: Skip ahead until we reach the
                # "BONUS SLIDES" sentinel.
                case "only" if not reached_bonus_slides_sentinel:
                    continue

            # Skip all sentinel (e.g., non-content) slides
            if slide in ("TENTATIVE", "BONUS SLIDES"):
                continue

            match finality:
                # Only final slides: Skip any non-final (e.g., tentative) slides
                case "only-final":
                    if _get_finality(slide) != "final":
                        continue
                # Only tentative slides: Skip any non-tentative (e.g., final) slides
                case "only-tentative" if not reached_tentative_sentinel:
                    if _get_finality(slide) != "tentative":
                        continue

            yield slide


def _get_finality(slide: ContentSlide) -> Finality:
    # Mypy (1.4.1 as of this writing) thinks this `isinstance` check with union is
    # illegal. It is not. It's a feature of python 3.10.
    if isinstance(slide, ItemSlide):  # type: ignore[misc,arg-type]
        return slide.finality  # type: ignore[union-attr]
    if isinstance(slide, str):
        return "tentative" if slide.endswith("?") else "final"
    raise ValueError(f"Unknown keynote slide type: '{type(slide).__name__}'")
