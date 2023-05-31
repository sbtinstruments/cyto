# pylint:disable=duplicate-code
from cyto.stout import Outcome, ResultMap
from cyto.stout.keynote import FinalItem, Keynote, Subset, TentativeItem


def test_outcome_with_keynote() -> None:
    raw_keynote = [
        {"intact cells/ml ⊆ total particles/ml": "12 000 ⊆ 50 000"},
        {"flow_rate?": 32.1},
        {"ID": "A03"},
        {"Meaning of Life": 42},
    ]
    raw_result = {
        "keynote": raw_keynote,
        "my_fav_number": 3.14,
    }
    raw_outcome = {"result": raw_result}
    # Deserialize
    outcome = Outcome.parse_obj(raw_outcome)
    assert isinstance(outcome.result, ResultMap)
    assert isinstance(outcome.result.keynote, Keynote)
    assert isinstance(outcome.result.keynote[0], Subset)
    assert isinstance(outcome.result.keynote[1], TentativeItem)
    assert isinstance(outcome.result.keynote[2], FinalItem)
    assert isinstance(outcome.result.keynote[3], FinalItem)
    assert outcome.result["my_fav_number"] == 3.14


def test_basic_outcome() -> None:
    raw_result = {
        "_report": {"analysis": "...something...", "algResult": {"even more!"}},
        "my_fav_number": 3.14,
    }
    raw_outcome = {"result": raw_result}
    # Deserialize
    outcome = Outcome.parse_obj(raw_outcome)
    assert isinstance(outcome.result, ResultMap)
    assert isinstance(outcome.result.keynote, Keynote)
    assert not outcome.result.keynote, "keynote is empty"
    assert isinstance(outcome.result["_report"], dict)
    assert outcome.result["my_fav_number"] == 3.14


def test_default_outcome() -> None:
    outcome = Outcome.parse_obj({})
    assert isinstance(outcome.result, ResultMap)
    assert isinstance(outcome.result.keynote, Keynote)
    assert not outcome.result.keynote, "keynote is empty"
    assert not outcome.result, "result is empty"
    assert not outcome.messages, "messages is empty"
    assert not outcome, "outcome is empty"
