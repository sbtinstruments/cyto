from cyto.stout.keynote import Item, Keynote, Subset, TentativeItem


def test_basic_keynote() -> None:
    raw_keynote = [
        {"intact cells/ml ⊆ total particles/ml": "12 000 ⊆ 50 000"},
        {"flow_rate?": 32.1},
        {"ID": "A03"},
        {"Meaning of Life": 42},
    ]
    # Deserialize (from list of dicts)
    keynote = Keynote.parse_obj(raw_keynote)
    assert keynote[0] == Subset(
        lhs=Item(key="intact cells/ml", value="12 000"),
        rhs=Item(key="total particles/ml", value="50 000"),
    )
    assert keynote[1] == TentativeItem(key="flow_rate", value=32.1)
    assert keynote[2] == Item(key="ID", value="A03")
    assert keynote[3] == Item(key="Meaning of Life", value=42)
    # Serialize (to list of dicts)
    assert list(keynote) == raw_keynote

    # The empty keynote is False
    assert bool(Keynote()) is False
