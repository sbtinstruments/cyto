from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from typing import Any, overload

from pydantic import parse_obj_as, root_validator

from ...model import FrozenModel
from ._keynote_tokens import SectionBeginToken, TagToken, Token

WIP_TAG = TagToken(__root__="[work-in-progress]")
BONUS_SECTION = SectionBeginToken(__root__="# Bonus slides")


class KeynoteTokenSeq(FrozenModel, Sequence[Token]):
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

    __root__: tuple[Token, ...] = ()

    @root_validator()
    def _validate_sentinels(cls, values: dict[str, Any]) -> dict[str, Any]:
        root = values["__root__"]

        ## The `[work-in-progress]` tag
        wip_tags = tuple(
            token for token in root if isinstance(token, TagToken) and token == WIP_TAG
        )
        # "[work-in-progress]" tag MUST be the first token
        if wip_tags and root[0] != WIP_TAG:
            raise ValueError("The '[work-in-progress]' tag must be the first token")
        # "[work-in-progress]" tag MUST be unique
        if len(wip_tags) > 1:
            raise ValueError("There can only be one '[work-in-progress]' tag")

        ## The `# Bonus slides` section
        sections = tuple(
            token for token in root if isinstance(token, SectionBeginToken)
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
        return values

    @overload
    def __getitem__(self, item: int) -> Token:
        ...

    @overload
    def __getitem__(self, _slice: slice) -> Sequence[Token]:
        ...

    def __getitem__(self, item: Any) -> Any:
        return self.__root__[item]

    # TODO: Use the `override` decorator when we get python 3.12
    def __iter__(self) -> Iterator[Token]:  # type: ignore[override]
        return iter(self.__root__)

    def __len__(self) -> int:
        return len(self.__root__)

    def __add__(self, rhs: Any) -> KeynoteTokenSeq:
        """Return a copy with the given tokens appended.

        Returns a copy. Does *not* mutate this instance.
        """
        if isinstance(rhs, Iterable):
            return KeynoteTokenSeq(__root__=(*self.__root__, *rhs))
        token = parse_obj_as(Token, rhs)  # type: ignore[var-annotated, arg-type]
        return KeynoteTokenSeq(__root__=(*self.__root__, token))

    def to_raw_seq(self) -> Sequence[str | dict[str, Any]]:
        """Convert to sequence of raw tokens."""
        result = self.dict()["__root__"]
        assert isinstance(result, Sequence)
        return result
