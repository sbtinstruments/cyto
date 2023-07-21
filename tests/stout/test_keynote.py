import pytest
from pydantic import ValidationError

from cyto.stout.keynote import FinalItem, Keynote, Subset, TentativeItem


def test_io() -> None:
    raw_keynote = [
        "TENTATIVE",
        {"intact cells/ml ⊆ total particles/ml": "12 000 ⊆ 50 000"},
        {"flow_rate?": 32.1},
        {"ID": "A03"},
        {"Meaning of Life": 42},
        "BONUS SLIDES",
        {"red cards? ⊆ all cards": "3 ⊆ 52"},
        {"red cards ⊆ all cards": "26 ⊆ 52"},
        "The QC test passed",
    ]
    # Deserialize (from list of dicts)
    keynote = Keynote.parse_obj(raw_keynote)
    assert keynote[0] == "TENTATIVE"
    assert keynote[1] == Subset(
        lhs=FinalItem(key="intact cells/ml", value="12 000"),
        rhs=FinalItem(key="total particles/ml", value="50 000"),
    )
    assert keynote[2] == TentativeItem(key="flow_rate", value=32.1)
    assert keynote[3] == FinalItem(key="ID", value="A03")
    assert keynote[4] == FinalItem(key="Meaning of Life", value=42)
    assert keynote[5] == "BONUS SLIDES"
    assert keynote[6] == Subset(
        lhs=TentativeItem(key="red cards", value=3),
        rhs=FinalItem(key="all cards", value=52),
    )
    assert keynote[7] == Subset(
        lhs=FinalItem(key="red cards", value=26),
        rhs=FinalItem(key="all cards", value=52),
    )
    assert keynote[8] == "The QC test passed"
    assert keynote.finality == "tentative"
    # Serialize (to list)
    assert list(keynote) == raw_keynote


def test_tentative_sentinel() -> None:
    keynote = Keynote.parse_obj(["TENTATIVE", {"ID": "A03"}])
    assert keynote[0] == "TENTATIVE"

    with pytest.raises(
        ValidationError,
        match="The 'TENTATIVE' slide must be the first slide",
    ):
        Keynote.parse_obj([{"ID": "A03"}, "TENTATIVE"])

    with pytest.raises(
        ValidationError,
        match="The 'TENTATIVE' slide must be the first slide",
    ):
        Keynote.parse_obj(["BONUS SLIDES", "TENTATIVE"])

    with pytest.raises(
        ValidationError,
        match="There can only be one 'TENTATIVE' slide",
    ):
        Keynote.parse_obj(["TENTATIVE", {"ID": "A03"}, "TENTATIVE"])

    with pytest.raises(
        ValidationError,
        match="There can only be one 'TENTATIVE' slide",
    ):
        Keynote.parse_obj(["TENTATIVE", "TENTATIVE", {"ID": "A03"}])


def test_bonus_slides_sentinel() -> None:
    with pytest.raises(
        ValidationError,
        match="There can only be one 'BONUS SLIDES' slide",
    ):
        Keynote.parse_obj(["BONUS SLIDES", "BONUS SLIDES"])


def test_content_filters() -> None:
    keynote = Keynote.parse_obj(["TENTATIVE", "Precisely 42"])

    tentative_content = list(keynote.content(finality="only-tentative"))
    assert tentative_content == ["Precisely 42"], (
        "Even though 'Precisely 42' is final, it counts as tentative content due "
        "to the 'TENTATIVE' sentinel."
    )

    keynote = Keynote.parse_obj([{"ID": "A03"}])
    keynote_with_bonus = keynote + ["BONUS SLIDES", {"flow_rate?": 32.1}]

    # Exclude bonus slides
    assert (
        Keynote(__root__=keynote_with_bonus.content(bonus_slides="exclude")) == keynote
    )

    # Include bonus slides
    assert Keynote(
        __root__=keynote_with_bonus.content(bonus_slides="include")
    ) == Keynote.parse_obj([{"ID": "A03"}, {"flow_rate?": 32.1}])

    # Only bonus slides
    assert Keynote(
        __root__=keynote_with_bonus.content(bonus_slides="only")
    ) == Keynote.parse_obj([{"flow_rate?": 32.1}])


def test_finality() -> None:
    # Single, final item
    keynote_final_item = Keynote.parse_obj([{"ID": "A03"}])
    assert keynote_final_item.finality == "final"

    # Single, tentative item
    keynote_tentative_item = Keynote.parse_obj([{"ID?": "A03"}])
    assert keynote_tentative_item.finality == "tentative"

    # Single, TENTATIVE sentinel slide
    keynote_only_tentative_sentinel = Keynote.parse_obj(["TENTATIVE"])
    assert keynote_only_tentative_sentinel.finality == "tentative"

    # The empty keynote
    empty_keynote = Keynote()
    assert bool(empty_keynote) is False
    assert empty_keynote.finality == "final"

    # Single, tentative string
    keynote_tentative_string = Keynote.parse_obj(["This is the meaning of life?"])
    assert keynote_tentative_string.finality == "tentative"

    # Single, final string
    keynote_final_string = Keynote.parse_obj(["This is the meaning of life"])
    assert keynote_final_string.finality == "final"

    keynote_bonus_slides = Keynote.parse_obj(
        [{"ID": "A03"}, "BONUS SLIDES", {"flow_rate?": 32.1}]
    )
    # Finality with bonus slides
    assert (
        keynote_bonus_slides.finality == "final"
    ), "Bonus slides does not count in terms of finality"
    assert Keynote.parse_obj(["BONUS SLIDES"]).finality == "final"
    assert Keynote.parse_obj(["TENTATIVE", "BONUS SLIDES"]).finality == "tentative"
