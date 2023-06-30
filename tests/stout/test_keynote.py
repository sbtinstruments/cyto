from cyto.stout.keynote import FinalItem, Keynote, Subset, TentativeItem


def test_basic_keynote() -> None:
    raw_keynote = [
        {"intact cells/ml ⊆ total particles/ml": "12 000 ⊆ 50 000"},
        {"flow_rate?": 32.1},
        {"ID": "A03"},
        {"Meaning of Life": 42},
        {"red cards? ⊆ all cards": "3 ⊆ 52"},
        {"red cards ⊆ all cards": "26 ⊆ 52"},
        "The QC test passed",
        "TENTATIVE",
    ]
    # Deserialize (from list of dicts)
    keynote = Keynote.parse_obj(raw_keynote)
    assert keynote[0] == Subset(
        lhs=FinalItem(key="intact cells/ml", value="12 000"),
        rhs=FinalItem(key="total particles/ml", value="50 000"),
    )
    assert keynote[1] == TentativeItem(key="flow_rate", value=32.1)
    assert keynote[2] == FinalItem(key="ID", value="A03")
    assert keynote[3] == FinalItem(key="Meaning of Life", value=42)
    assert keynote[4] == Subset(
        lhs=TentativeItem(key="red cards", value=3),
        rhs=FinalItem(key="all cards", value=52),
    )
    assert keynote[5] == Subset(
        lhs=FinalItem(key="red cards", value=26),
        rhs=FinalItem(key="all cards", value=52),
    )
    assert keynote[6] == "The QC test passed"
    assert keynote[7] == "TENTATIVE"
    assert keynote.finality == "tentative"
    # Serialize (to list)
    assert list(keynote) == raw_keynote

    # Single, definite item
    keynote0 = Keynote.parse_obj([{"ID": "A03"}])
    assert keynote0.finality == "final"

    # Single, tentative item
    keynote1 = Keynote.parse_obj([{"ID?": "A03"}])
    assert keynote1.finality == "tentative"

    # Single, TENTATIVE sentinel slide
    keynote2 = Keynote.parse_obj(["TENTATIVE"])
    assert keynote2.finality == "tentative"

    # The empty keynote
    empty_keynote = Keynote()
    assert bool(empty_keynote) is False
    assert empty_keynote.finality == "final"

    # Single, tentative string
    keynote3 = Keynote.parse_obj(["This is the meaning of life?"])
    assert keynote3.finality == "tentative"

    # Single, final string
    keynote4 = Keynote.parse_obj(["This is the meaning of life"])
    assert keynote4.finality == "final"
