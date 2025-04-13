from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import Annotated, Any, ClassVar, Literal, Self

from pydantic import (
    AfterValidator,
    GetJsonSchemaHandler,
    ValidatorFunctionWrapHandler,
    model_serializer,
    model_validator,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema

from cyto.model import FrozenModel

from ._keynote_token_seq import WIP_TAG, KeynoteTokenSeq
from ._keynote_tokens import (
    FinalItem,
    Finality,
    ItemToken,
    SectionBeginToken,
    SlideToken,
    Subset,
    TagToken,
    TentativeItem,
    Token,
    ValueType,
)

BonusSlidesFilter = Literal["exclude", "include", "only"]
FinalityFilter = Literal["only-final", "only-tentative", "include-all"]
SlideSeq = tuple[SlideToken, ...]


class KeynoteSection(FrozenModel):
    name: str = "__anon__"
    slides: SlideSeq = ()

    def __bool__(self) -> bool:
        return bool(self.slides)


def _validate_section_seq(
    section_seq: tuple[KeynoteSection, ...],
) -> tuple[KeynoteSection, ...]:
    names = tuple(section.name for section in section_seq)
    if len(names) != len(frozenset(names)):
        raise ValueError("Sections must have unique names")
    if names and "Bonus slides" in names and names[-1] != "Bonus slides":
        raise ValueError("The 'Bonus slides' section must come last")
    return section_seq


SectionSeq = Annotated[
    tuple[KeynoteSection, ...], AfterValidator(_validate_section_seq)
]


class Keynote(FrozenModel):
    """Keynote slides grouped into sections.

    This is the primary keynote "view". You usually use this `Keynote` class and don't
    deal with the low-level `KeynoteTokenSeq` class. The `Keynote` class takes the
    sentinel tokens (e.g., `[work-in-progress]`, `# Bonus slides`) into account and
    allows you to filter on them.
    """

    work_in_progress: bool = False
    section_type: ClassVar[type] = KeynoteSection
    sections: SectionSeq = ()

    @classmethod
    def __get_pydantic_json_schema__(
        cls, cs: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return {
            # Match the `data` type in `_validate`
            "anyOf": [
                handler(cs),
                handler(KeynoteTokenSeq.__pydantic_core_schema__),
            ]
        }

    @model_validator(mode="wrap")
    @classmethod
    def _validate(cls, data: Any, handler: ValidatorFunctionWrapHandler) -> Any:
        if isinstance(data, Sequence):
            return cls.from_token_seq(data)
        return handler(data)

    @model_serializer()
    def _serialize(self) -> Sequence[str | dict[str, Any]]:
        # TODO: Add WIP tag as well based on `work_in_progress`
        return self.to_raw_seq()  # type: ignore[call-arg]

    @property
    def finality(self) -> Finality:
        """Return "tentative" if there is any tentative content.

        Otherwise, return "final".

        Note that:

         * The empty keynote is "final".
         * A keynote with a "[work-in-progress]" tag is "tentative".
         * Slides in the "Bonus slides" section do not count.

        """
        tentative_content = self.content(
            bonus_slides="exclude", finality="only-tentative"
        )
        if tentative_content or self.work_in_progress:
            return "tentative"
        return "final"

    def content(
        self,
        *,
        bonus_slides: BonusSlidesFilter | None = None,
        finality: FinalityFilter | None = None,
        remove_empty_sections: bool | None = None,
    ) -> Keynote:
        """Return copy with the given content filters applied.

        Does *not* modify this instance. Returns a copy instead.


        ## Default values

        Note that this function:

         * Excludes bonus slides per default.
           Use `bonus_filter` to override this.
         * Includes both tentative and final slides per default.
           Use `finality_filter` to override this.
         * Removes empty sections per default.
           Use `remove_empty_sections` to override this.
        """
        if bonus_slides is None:
            bonus_slides = "exclude"
        if finality is None:
            finality = "include-all"
        if remove_empty_sections is None:
            remove_empty_sections = True

        sections = self.sections
        sections = _apply_bonus_slides_filter_to_sections(sections, bonus_slides)
        sections = _apply_finality_filter_to_sections(sections, finality)
        if remove_empty_sections:
            sections = _remove_empty_sections(sections)
        return Keynote(work_in_progress=self.work_in_progress, sections=sections)

    def __bool__(self) -> bool:
        return bool(self.sections)

    @classmethod
    def from_token_seq(
        cls: type[Self],
        token_seq: KeynoteTokenSeq | Iterable[Any],
    ) -> Self:
        """Return instance created from the given token sequence.


        ## Analogy to computer language theory

        It might be useful to draw analogy to computer language theory:

         * Source code: List of raw slides (e.g., `["Welcome", {"ID?": "A03"}]`)
         * Lexer: The `KeynoteTokenSeq.parse_obj` that we get from pydantic
         * Tokens: A `KeynoteTokenSeq` instance (tuple of `Slide`s)
         * Parser: The `Keynote.from_token_seq` function
         * Abstract syntax tree (AST): An instance of `Keynote`

        These concepts connect like this:

            Source code --(lexer)--> Tokens --(parser)--> AST

        In this analogy, the `KeynoteTokenSeq` itself is just a sequence of tokens.
        Not very meaningful on their own; more like an intermediate calculation.
        After we call `Keynote.from_token_seq`, we get the AST. We can use the AST
        directly.

        Note that this analogy does not hold up completely since
        `KeynoteTokenSeq._validate_sentinels` goes beyond the scope of what a lexer
        would do.
        """
        if not isinstance(token_seq, KeynoteTokenSeq):
            token_seq = KeynoteTokenSeq.model_validate(token_seq)
        if not token_seq:
            return Keynote()  # type: ignore[return-value]
        first_token = token_seq[0]
        work_in_progress = first_token == WIP_TAG
        sections = _tokens_to_sections(token_seq, section_type=cls.section_type)
        return cls(work_in_progress=work_in_progress, sections=sections)

    def to_raw_seq(self) -> Sequence[str | dict[str, Any]]:
        """Convert to raw token sequence."""
        token_seq = self.to_token_seq()
        result = token_seq.to_raw_seq()
        assert isinstance(result, Sequence)
        return result

    def to_token_seq(self) -> KeynoteTokenSeq:
        """Convert to token sequence."""
        return KeynoteTokenSeq(root=tuple(self._to_tokens()))

    def _to_tokens(self) -> Iterable[Token]:
        if self.work_in_progress:
            yield WIP_TAG
        for section in self.sections:
            if section.name != "__anon__":
                yield SectionBeginToken(root=f"# {section.name}")
            yield from section.slides

    def get_values(self, *keys: str) -> Iterable[ValueType | None]:
        """Search for the given keys in this keynote.

        Returns `None` for keys that we could not find.
        If there are duplicate entries for a key, we return the value of the
        first entry.

        Worst-case runtime is `O(n*m)` where `n` is the number of slides in this
        keynote and `m` is the number of keys to search for.
        """
        # Worst-case runtime: `O(n*m)`
        for search_key in keys:  # `m`: number of keys
            matching_values = (
                value for key, value in self._items() if key == search_key
            )
            for matching_value in matching_values:  # `n`: number of slides
                yield matching_value
                break
            else:  # no break (key not found)
                yield None

    def _items(self) -> Iterable[tuple[str, ValueType]]:
        slides = tuple(slide for section in self.sections for slide in section.slides)
        for slide in slides:
            if isinstance(slide, TentativeItem | FinalItem):
                yield (slide.key, slide.value)
            elif isinstance(slide, Subset):
                yield (slide.lhs.key, slide.lhs.value)
                yield (slide.rhs.key, slide.rhs.value)


def _apply_bonus_slides_filter_to_sections(
    sections: SectionSeq, bonus_slides: BonusSlidesFilter
) -> SectionSeq:
    match bonus_slides:
        case "exclude":
            return tuple(
                section for section in sections if section.name != "Bonus slides"
            )
        case "only":
            return tuple(
                section for section in sections if section.name == "Bonus slides"
            )
        case "include":
            return sections
        case _:
            raise ValueError(f"Invalid 'BonusSlidesFilter' value: '{bonus_slides}'")


def _apply_finality_filter_to_sections(
    sections: SectionSeq, finality: FinalityFilter
) -> SectionSeq:
    return tuple(
        KeynoteSection(
            name=section.name,
            slides=tuple(_apply_finality_filter_to_slides(section.slides, finality)),
        )
        for section in sections
    )


def _apply_finality_filter_to_slides(
    slides: Iterable[SlideToken], finality: FinalityFilter
) -> Iterable[SlideToken]:
    match finality:
        case "only-final":
            return (slide for slide in slides if _get_finality(slide) == "final")
        case "only-tentative":
            return (slide for slide in slides if _get_finality(slide) == "tentative")
        case "include-all":
            return slides
        case _:
            raise ValueError(f"Invalid 'FinalityFilter' value: '{finality}'")


def _get_finality(slide: SlideToken) -> Finality:
    # Mypy (1.4.1 as of this writing) thinks this `isinstance` check with union is
    # illegal. It is not. It's a feature of python 3.10.
    if isinstance(slide, ItemToken):  # type: ignore[misc,arg-type]
        return slide.finality  # type: ignore[union-attr]
    if isinstance(slide, str):
        return "tentative" if slide.endswith("?") else "final"
    raise ValueError(f"Unknown keynote slide type: '{type(slide).__name__}'")


def _remove_empty_sections(sections: SectionSeq) -> SectionSeq:
    return tuple(section for section in sections if section)


def _tokens_to_sections(token_seq: KeynoteTokenSeq, section_type: type) -> SectionSeq:
    result: defaultdict[str, list[SlideToken]] = defaultdict(list)
    section_name = "__anon__"
    for token in token_seq:
        match token:
            case SectionBeginToken(name=section_name):  # type: ignore[misc]
                continue
            case TagToken():  # type: ignore[misc]
                # Ignore all other sentinels
                continue
            case _:
                result[section_name].append(token)
    return tuple(
        section_type(name=name, slides=slides) for name, slides in result.items()
    )
