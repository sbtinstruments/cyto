# ruff: noqa: PLR2004, N806
from typing import Annotated

import pytest
from pydantic import AfterValidator, Field, NonNegativeInt, ValidationError

from cyto.model import AssignOp, FrozenModel, Patch, PatchError, Stitch


class Evaluation(FrozenModel):
    overall_rating: Annotated[int, Field(ge=1, le=10)]


class CakeLayer(FrozenModel):
    description: str
    contains_lactose: bool = False
    evaluation: Evaluation | None = None


class Cake(FrozenModel):
    name: str
    candle_count: NonNegativeInt = 0
    layers: tuple[CakeLayer, ...] = ()


class CompanyEvent(FrozenModel):
    occation: str
    cake: Cake | None = None


def _create_birthday_event() -> CompanyEvent:
    return CompanyEvent(
        occation="birthday",
        cake=Cake(
            name="strawberry-cake",
            layers=[
                CakeLayer(
                    description="shortcut-pastry",
                    contains_lactose=True,
                    evaluation=Evaluation(overall_rating=7),
                ),
                CakeLayer(description="chocolate-paste", contains_lactose=True),
                CakeLayer(description="vanilla-cream", contains_lactose=True),
                CakeLayer(description="strawberry"),
                CakeLayer(description="gel"),
            ],
        ),
    )


def test_patch_parser() -> None:
    dict_patch = {"cake.name": "berrynator"}
    patch = Patch.from_dict(dict_patch)
    assert patch == Patch(
        stitches=(Stitch(path="cake.name", operation=AssignOp(value="berrynator")),)
    )


def test_stitch_apply() -> None:
    event = CompanyEvent(occation="christmas", cake=Cake(name="flat-cake"))

    stitch = Stitch(path="cake.name", operation=AssignOp(value="berrynator"))
    patched_event = stitch.apply(event)
    assert patched_event == CompanyEvent(
        occation="christmas", cake=Cake(name="berrynator")
    )

    stitch = Stitch(path="cake.flavour", operation=AssignOp(value="sweet"))
    with pytest.raises(PatchError):
        stitch.apply(event)


def test_frozen_model() -> None:
    event = _create_birthday_event()

    # Empty patch
    new_event = event.frozen_patch({})
    assert new_event == _create_birthday_event()

    # Root-level patch
    new_event = event.frozen_patch({"occation": "townhall"})
    assert new_event == CompanyEvent(
        occation="townhall",
        cake=Cake(
            name="strawberry-cake",
            layers=[
                CakeLayer(
                    description="shortcut-pastry",
                    contains_lactose=True,
                    evaluation=Evaluation(overall_rating=7),
                ),
                CakeLayer(description="chocolate-paste", contains_lactose=True),
                CakeLayer(description="vanilla-cream", contains_lactose=True),
                CakeLayer(description="strawberry"),
                CakeLayer(description="gel"),
            ],
        ),
    )

    # Submodel patch
    new_event = event.frozen_patch({"cake.name": "berrynator"})
    assert new_event == CompanyEvent(
        occation="birthday",
        cake=Cake(
            name="berrynator",
            layers=[
                CakeLayer(
                    description="shortcut-pastry",
                    contains_lactose=True,
                    evaluation=Evaluation(overall_rating=7),
                ),
                CakeLayer(description="chocolate-paste", contains_lactose=True),
                CakeLayer(description="vanilla-cream", contains_lactose=True),
                CakeLayer(description="strawberry"),
                CakeLayer(description="gel"),
            ],
        ),
    )

    # Erroneous patch
    with pytest.raises(ValidationError):
        event.frozen_patch({"cake.candle_count": "twenty-four"})


def test_example_given_in_frozen_model_docstring() -> None:
    Squared = Annotated[int, AfterValidator(lambda v: v**2)]

    class MyModel(FrozenModel):
        my_int: int
        my_square: Squared

    my_model = MyModel(my_int=2, my_square=3)
    assert my_model.my_int == 2
    assert my_model.my_square == 9  # 3 squared

    patched_model = my_model.frozen_patch({"my_int": 7}, validation="full")
    assert patched_model.my_int == 7
    assert patched_model.my_square == 81  # 9 squared!

    patched_model = my_model.frozen_patch({"my_int": 7}, validation="immutable")
    assert patched_model.my_int == 7
    assert patched_model.my_square == 9  # 3 squared


def test_frozen_patch_with_mutating_validator() -> None:
    Squared = Annotated[int, AfterValidator(lambda v: v**2)]

    class MyModel(FrozenModel):
        my_int: int
        my_first_square: Squared
        my_second_square: Squared = 7

    ### Some fields left at the default value
    my_model = MyModel(my_int=2, my_first_square=3)
    assert my_model.my_int == 2
    assert my_model.my_first_square == 3**2
    # Note that it doesn't validate default values (unless you explicitly opt in
    # to this behaviour with `validate_default=True`)
    assert my_model.my_second_square == 7

    patched_model = my_model.frozen_patch({"my_first_square": 5})
    assert patched_model.my_int == 2
    assert patched_model.my_first_square == 5**2
    assert patched_model.my_second_square == 7

    # No change to the original
    assert my_model.my_int == 2
    assert my_model.my_first_square == 3**2
    assert my_model.my_second_square == 7

    ### All fields specified on init
    my_model = MyModel(my_int=2, my_first_square=3, my_second_square=8)
    assert my_model.my_int == 2
    assert my_model.my_first_square == 3**2
    assert my_model.my_second_square == 8**2

    patched_model = my_model.frozen_patch({"my_first_square": 5})
    assert patched_model.my_int == 2
    assert patched_model.my_first_square == 5**2
    # Note that the result is now 8^4 since the patch operation applies the
    # `Squared` validator *again*!
    assert patched_model.my_second_square == 4096

    twice_patched_model = patched_model.frozen_patch({"my_first_square": 5})
    assert twice_patched_model.my_int == 2
    assert twice_patched_model.my_first_square == 5**2
    # Note that the validator is applied *again*
    assert twice_patched_model.my_second_square == 16777216