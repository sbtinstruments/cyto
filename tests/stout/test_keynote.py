import pytest
from pydantic import ValidationError

from cyto.stout.keynote import (
    FinalItem,
    Keynote,
    KeynoteSection,
    KeynoteTokenSeq,
    MutableKeynote,
    MutableKeynoteSection,
    Subset,
    TentativeItem,
)
from cyto.stout.keynote._keynote_token_seq import WIP_TAG
from cyto.stout.keynote._keynote_tokens import SectionBeginToken, TagToken

_RAW_KEYNOTE = [
    "[work-in-progress]",
    {"intact cells/ml ⊆ total particles/ml": "12 000 ⊆ 50 000"},
    "# Some stuff",
    {"flow_rate?": 32.1},
    {"ID": "A03"},
    {"Meaning of Life": 42},
    "# Bonus slides",
    {"red cards? ⊆ all cards": "3 ⊆ 52"},
    {"red cards ⊆ all cards": "26 ⊆ 52"},
    "The QC test passed",
]


def test_token_io() -> None:
    # Deserialize (from list)
    token_seq = KeynoteTokenSeq.model_validate(_RAW_KEYNOTE)
    assert token_seq[0] == TagToken(root="[work-in-progress]")
    assert token_seq[1] == Subset(
        lhs=FinalItem(key="intact cells/ml", value="12 000"),
        rhs=FinalItem(key="total particles/ml", value="50 000"),
    )
    assert token_seq[2] == SectionBeginToken(root="# Some stuff")
    assert token_seq[3] == TentativeItem(key="flow_rate", value=32.1)
    assert token_seq[4] == FinalItem(key="ID", value="A03")
    assert token_seq[5] == FinalItem(key="Meaning of Life", value=42)
    assert token_seq[6] == SectionBeginToken(root="# Bonus slides")
    assert token_seq[7] == Subset(
        lhs=TentativeItem(key="red cards", value=3),
        rhs=FinalItem(key="all cards", value=52),
    )
    assert token_seq[8] == Subset(
        lhs=FinalItem(key="red cards", value=26),
        rhs=FinalItem(key="all cards", value=52),
    )
    assert token_seq[9] == "The QC test passed"
    # Serialize (to list)
    assert list(token_seq.to_raw_seq()) == _RAW_KEYNOTE


def test_work_in_progress_token() -> None:
    keynote = KeynoteTokenSeq.model_validate(["[work-in-progress]", {"ID": "A03"}])
    assert keynote[0] == TagToken(root="[work-in-progress]")

    with pytest.raises(
        ValidationError,
        match=r"The '\[work-in-progress\]' tag must be the first token",
    ):
        KeynoteTokenSeq.model_validate([{"ID": "A03"}, "[work-in-progress]"])

    with pytest.raises(
        ValidationError,
        match=r"The '\[work-in-progress\]' tag must be the first token",
    ):
        KeynoteTokenSeq.model_validate(["# Bonus slides", "[work-in-progress]"])

    with pytest.raises(
        ValidationError,
        match=r"There can only be one '\[work-in-progress\]' tag",
    ):
        KeynoteTokenSeq.model_validate(
            ["[work-in-progress]", {"ID": "A03"}, "[work-in-progress]"]
        )

    with pytest.raises(
        ValidationError,
        match=r"There can only be one '\[work-in-progress\]' tag",
    ):
        KeynoteTokenSeq.model_validate(
            ["[work-in-progress]", "[work-in-progress]", {"ID": "A03"}]
        )


def test_bonus_slides_token() -> None:
    with pytest.raises(
        ValidationError,
        match="The '# Bonus slides' section must be the last section",
    ):
        KeynoteTokenSeq.model_validate(["# Bonus slides", "# My section"])

    with pytest.raises(
        ValidationError,
        match="There can only be one '# Bonus slides' section",
    ):
        KeynoteTokenSeq.model_validate(["# Bonus slides", "# Bonus slides"])


def test_keynote_io() -> None:
    # Deserialize (from list)
    keynote = Keynote.from_token_seq(_RAW_KEYNOTE)
    assert Keynote(
        work_in_progress=True,
        sections=(
            KeynoteSection(
                slides=(
                    Subset(
                        lhs=FinalItem(key="intact cells/ml", value="12 000"),
                        rhs=FinalItem(key="total particles/ml", value="50 000"),
                    ),
                )
            ),
            KeynoteSection(
                name="Some stuff",
                slides=(
                    TentativeItem(key="flow_rate", value=32.1),
                    FinalItem(key="ID", value="A03"),
                    FinalItem(key="Meaning of Life", value=42),
                ),
            ),
            KeynoteSection(
                name="Bonus slides",
                slides=(
                    Subset(
                        lhs=TentativeItem(key="red cards", value=3),
                        rhs=FinalItem(key="all cards", value=52),
                    ),
                    Subset(
                        lhs=FinalItem(key="red cards", value=26),
                        rhs=FinalItem(key="all cards", value=52),
                    ),
                    "The QC test passed",
                ),
            ),
        ),
    )
    # Serialize (to list)
    assert list(keynote.to_raw_seq()) == _RAW_KEYNOTE


def test_content_filters() -> None:
    keynote = Keynote.from_token_seq(["[work-in-progress]", "Precisely 42"])

    # Final content
    final_content = keynote.content(finality="only-final")
    assert final_content == Keynote(
        work_in_progress=True, sections=(KeynoteSection(slides=["Precisely 42"]),)
    ), (
        "Even though there is a '[work-in-progress]' tag, the 'Precisely 42' "
        "item is still is final"
    )

    # Tentative content
    tentative_content = keynote.content(finality="only-tentative")
    assert not tentative_content, "In fact, there is no final content"
    assert keynote.finality == "tentative", (
        "The keynote as a whole, however, is tentative even though it only contains "
        "final content"
    )

    keynote = Keynote.from_token_seq([{"ID": "A03"}])
    keynote_with_bonus = Keynote.from_token_seq(
        [
            {"ID": "A03"},
            "# Bonus slides",
            {"flow_rate?": 32.1},
        ]
    )

    # Exclude bonus slides
    assert keynote_with_bonus.content(bonus_slides="exclude") == keynote
    # Include bonus slides
    assert keynote_with_bonus.content(bonus_slides="include") == keynote_with_bonus
    # Only bonus slides
    assert keynote_with_bonus.content(bonus_slides="only") == Keynote(
        sections=(
            KeynoteSection(
                name="Bonus slides", slides=[TentativeItem(key="flow_rate", value=32.1)]
            ),
        )
    )


def test_finality() -> None:
    # Single, final item
    keynote_final_item = Keynote.from_token_seq([{"ID": "A03"}])
    assert keynote_final_item.finality == "final"

    # Single, tentative item
    keynote_tentative_item = Keynote.from_token_seq([{"ID?": "A03"}])
    assert keynote_tentative_item.finality == "tentative"

    # Single, [work-in-progress] tag
    keynote_only_tentative_sentinel = Keynote.from_token_seq(["[work-in-progress]"])
    assert keynote_only_tentative_sentinel.finality == "tentative"

    # The empty keynote
    empty_keynote = Keynote()
    assert bool(empty_keynote) is False
    assert empty_keynote.finality == "final"

    # Single, tentative string
    keynote_tentative_string = Keynote.from_token_seq(["This is the meaning of life?"])
    assert keynote_tentative_string.finality == "tentative"

    # Single, final string
    keynote_final_string = Keynote.from_token_seq(["This is the meaning of life"])
    assert keynote_final_string.finality == "final"

    keynote_bonus_slides = Keynote.from_token_seq(
        [{"ID": "A03"}, "# Bonus slides", {"flow_rate?": 32.1}]
    )
    # Finality with bonus slides
    assert (
        keynote_bonus_slides.finality == "final"
    ), "Bonus slides does not count in terms of finality"
    assert Keynote.from_token_seq(["# Bonus slides"]).finality == "final"
    assert (
        Keynote.from_token_seq(["[work-in-progress]", "# Bonus slides"]).finality
        == "tentative"
    )


def test_mutable_keynote() -> None:
    keynote = Keynote.from_token_seq([{"ID": "A03"}])
    mutable_keynote = MutableKeynote.unfreeze(keynote)
    assert mutable_keynote.freeze() == keynote
    mutable_keynote.sections[0].slides = [{"ID": "B96"}]  # type: ignore[misc,list-item]
    assert mutable_keynote.freeze() == Keynote.from_token_seq([{"ID": "B96"}])

    keynote = Keynote.from_token_seq(
        [{"ID": "A03"}, "# Bonus slides", {"flow_rate?": 32.1}]
    )
    mutable_keynote = MutableKeynote.unfreeze(keynote)
    # We append a new section
    mutable_keynote.set_section(
        MutableKeynoteSection(name="My new section", slides=["It's a great message"])
    )
    # We override an existing section ("Bonus slides")
    # Note that we provide an immutable `KeynoteSection`. That's allowed.
    mutable_keynote.set_section(
        KeynoteSection(name="Bonus slides", slides=[{"flow_rate": 40.1}])
    )

    assert mutable_keynote.freeze() == Keynote.from_token_seq(
        [
            {"ID": "A03"},
            "# My new section",
            "It's a great message",
            "# Bonus slides",
            {"flow_rate": 40.1},
        ]
    )
    # Even though we provided an immutable `KeynoteSection` to `set_section`, the
    # corresponding section is still mutable. This is how it should be.
    assert mutable_keynote.sections[-1] == MutableKeynoteSection(
        name="Bonus slides", slides=[FinalItem(key="flow_rate", value=40.1)]
    )


def test_keynote_to_token_seq() -> None:
    keynote = Keynote(
        work_in_progress=True,
        sections=[
            KeynoteSection(
                name="Metadata",
                slides=[FinalItem(finality="final", key="ID", value="S87")],
            )
        ],
    )

    token_seq = keynote.to_token_seq()
    # Note that `BaseModel.__eq__` does *not* do `isinstance` checks (it merely
    # compares the underlying `dict` representations). Therefore, we add manual
    # `isinstance` checks here.
    assert isinstance(token_seq[0], TagToken)
    assert isinstance(token_seq[1], SectionBeginToken)
    assert isinstance(token_seq[2], FinalItem)
    assert keynote.to_token_seq() == KeynoteTokenSeq(
        root=(
            WIP_TAG,
            SectionBeginToken(root="# Metadata"),
            FinalItem(finality="final", key="ID", value="S87"),
        )
    )


def test_keynote_get_values() -> None:
    keynote = Keynote.from_token_seq(_RAW_KEYNOTE)
    assert (  # pylint: disable=use-implicit-booleaness-not-comparison
        tuple(keynote.get_values()) == ()
    )
    # Single, final item
    assert tuple(keynote.get_values("ID")) == ("A03",)
    # Multiple items: One tentative, one final
    assert tuple(keynote.get_values("flow_rate", "ID")) == (32.1, "A03")
    # ...and reversed argument order
    assert tuple(keynote.get_values("ID", "flow_rate")) == ("A03", 32.1)
    # Misspelled key
    assert tuple(keynote.get_values("ID", "fløw_raid")) == ("A03", None)
    # Duplicate keys:
    #
    # >    {"red cards? ⊆ all cards": "3 ⊆ 52"},
    # >    {"red cards ⊆ all cards": "26 ⊆ 52"},
    #
    assert tuple(keynote.get_values("red cards")) == (3,)
    assert tuple(keynote.get_values("all cards")) == (52,)
