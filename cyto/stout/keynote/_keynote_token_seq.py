from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from typing import Annotated, Any, Self, overload

from pydantic import (
    Field,
    RootModel,
    TypeAdapter,
    model_validator,
)

from ._keynote_tokens import SectionBeginToken, TagToken, Token

WIP_TAG = TagToken(root="[work-in-progress]")
BONUS_SECTION = SectionBeginToken(root="# Bonus slides")


class KeynoteTokenSeq(RootModel[tuple[Token, ...]], Sequence[Token], frozen=True):
    """Sequence of keynote tokens.

    Serializes to something like this:

        [
            "[work-in-progress]",
            { "ID": "A03" },
            "# Concentrations",
            { "intact cells/ml ⊆ total particles/ml": "12 000 ⊆ 50 000" },
            "# Bonus slides",
            { "flow_rate?": 32.1 },
            "Results look good"
        ]


    ## Special sentinel tokens

    ### The `[work-in-progress]` tag

    Use this tag to indicate that, overall, the keynote is tentative (even
    if it only contains "final" content). E.g., to denote that the you'll add
    additional slides later.

    MUST be the first token.
    MUST be unique (there can not be multiple `[work-in-progress]` tags).


    ### The `# Bonus slides` section

    Use this section to indicate that the slides within are nonessential.
    E.g., said slides represent additional information, deep dives, reference
    material, etc.

    MUST be the last section.
    MUST be unique (there can not be multiple `# Bonus slides` sections).

    """

    root: tuple[Token, ...] = ()

    @model_validator(mode="after")
    def _validate_sentinels(self) -> Self:
        ## The `[work-in-progress]` tag
        wip_tags = tuple(
            token
            for token in self.root
            if isinstance(token, TagToken) and token == WIP_TAG
        )
        # "[work-in-progress]" tag MUST be the first token
        if wip_tags and self.root[0] != WIP_TAG:
            raise ValueError("The '[work-in-progress]' tag must be the first token")
        # "[work-in-progress]" tag MUST be unique
        if len(wip_tags) > 1:
            raise ValueError("There can only be one '[work-in-progress]' tag")

        ## The `# Bonus slides` section
        sections = tuple(
            token for token in self.root if isinstance(token, SectionBeginToken)
        )
        bonus_sections = tuple(
            section for section in sections if section == BONUS_SECTION
        )
        # `# Bonus slides` section MUST be the last section
        if sections and bonus_sections and sections[-1] != BONUS_SECTION:
            raise ValueError("The '# Bonus slides' section must be the last section")
        # `# Bonus slides` section MUST be unique
        if len(bonus_sections) > 1:
            raise ValueError("There can only be one '# Bonus slides' section")
        return self

    @overload
    def __getitem__(self, item: int) -> Token: ...

    @overload
    def __getitem__(self, _slice: slice) -> Sequence[Token]: ...

    def __getitem__(self, item: Any) -> Any:
        return self.root[item]

    # TODO: Use the `override` decorator when we get python 3.12
    def __iter__(self) -> Iterator[Token]:  # type: ignore[override]
        return iter(self.root)

    def __len__(self) -> int:
        return len(self.root)

    def __add__(self, rhs: Any) -> KeynoteTokenSeq:
        """Return a copy with the given tokens appended.

        Returns a copy. Does *not* mutate this instance.
        """
        if isinstance(rhs, Iterable):
            return KeynoteTokenSeq(root=(*self.root, *rhs))
        token = TypeAdapter(Token).validate_python(rhs)  # type: ignore[var-annotated, arg-type]
        return KeynoteTokenSeq(root=(*self.root, token))

    def to_raw_seq(self) -> Sequence[str | dict[str, Any]]:
        """Convert to sequence of raw tokens."""
        return tuple(
            token if isinstance(token, str) else token.model_dump() for token in self
        )
