# ruff: noqa: PLR2004, N806
from typing import Annotated, Any, Literal

import pytest
from pydantic import (
    AfterValidator,
    Discriminator,
    Field,
    NonNegativeInt,
    RootModel,
    ValidationError,
)

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
    # Note that we validate the default value, which applies `Squared` to it.
    # This is the expected behaviour of `validation="full"` (the default).
    assert patched_model.my_second_square == 7**2

    # We can use `validation="immutable"` to avoid this behaviour
    patched_model = my_model.frozen_patch(
        {"my_first_square": 5}, validation="immutable"
    )
    assert patched_model.my_int == 2
    assert patched_model.my_first_square == 5
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


def test_frozen_patch_with_discriminated_union() -> None:
    """This test is in response to a specific issue.

    We got this error from within `frozen_patch`:

        pydantic_core._pydantic_core.ValidationError: 1 validation error for DspSettings
        method
          Unable to extract tag using discriminator 'name' [type=union_tag_not_found,
          input_value={}, input_type=dict]
            For further information visit https://errors.pydantic.dev/2.8/v/union_tag_not_found

    Turns out to be because we used `exclude_unset=True` inside `Patch.apply`. This
    was in an effort to avoid applying mutating validators to unset fields.
    Unfortunately, this doesn't work well together with the "discriminator" used
    with tagged unions. In practice, `exclude_unset=True` always removes the `name`
    field (the union discriminator). In turn, we get a ValidationError because said
    field is missing.

    The fix is simply to remove `exclude_unset=True`. If our users want to disable
    the effects of mutating validators, they can use the `validation="immutable"`
    option.
    """

    class CommonModeRejection(FrozenModel):
        name: Literal["common-mode-rejection"] = "common-mode-rejection"
        common_filter: str = "250-350hz--23khz--fir--32coeffs--v0.1.0"

    class CustomFunction(FrozenModel):
        name: Literal["custom-function"] = "custom-function"
        function_name: str

    DspMethod = Annotated[CommonModeRejection | CustomFunction, Discriminator("name")]

    class DspSettings(FrozenModel):
        method: DspMethod

    my_settings = DspSettings(method=CustomFunction(function_name="my_func"))
    patched_settings = my_settings.frozen_patch({"method": CommonModeRejection()})
    assert patched_settings.method == CommonModeRejection()


def test_frozen_patch_with_new_dict_item() -> None:
    from cyto.stout import Message, Outcome

    # Empty outcome
    outcome = Outcome()
    message = Message.error(
        tech_cause=(
            "Conductivity is too low (value is 123 µS/cm but minimum is 1000 µS/cm)"
        ),
        user_cause="The conductivity is lower than 1000 µS/cm",
        user_consequence="Sample cannot be measured",
        user_suggestion=("Conductivity was 123 µS/cm—adjust to 1000-2000 µS/cm"),
    )

    # We can not (yet) add items to a dictionary.
    with pytest.raises(PatchError):
        outcome = outcome.frozen_patch({"messages.1200": message})


def test_frozen_patch_with_set() -> None:
    class Idea(FrozenModel):
        desc: str

    class Brainstorm(FrozenModel):
        me_gusta: frozenset[Idea]

    orig_bs = Brainstorm(me_gusta=[Idea(desc="cars"), Idea(desc="tea")])

    ### Patch given as a list of ideas
    patched_bs = orig_bs.frozen_patch({"me_gusta": [Idea(desc="computers")]})
    assert isinstance(patched_bs.me_gusta, frozenset)
    assert patched_bs.me_gusta == {Idea(desc="computers")}

    ### Patch given as a frozenset directly
    # Note that `BaseModel.model_dump()` raises TypeError.
    # This is a known issue: https://github.com/pydantic/pydantic/issues/8016
    # As of this writing (2024-11-13) there is no plan to fix this
    # in pydantic.
    with pytest.raises(TypeError, match="unhashable type: 'dict'"):
        orig_bs.model_dump()

    # An early implementation of `frozen_patch` used `model_dump` internally.
    # This caused issues due to the `TypeError` mentioned above. This is no
    # longer the case with the latest implementation of `frozen_patch`. However,
    # we keep this test around to avoid regressions.
    patched_bs = orig_bs.frozen_patch({"me_gusta": frozenset([Idea(desc="computers")])})
    assert isinstance(patched_bs.me_gusta, frozenset)
    assert patched_bs.me_gusta == {Idea(desc="computers")}


def test_frozen_patch_with_type_fields() -> None:
    class NumberFactory(FrozenModel):
        result_type: type[Any] = float

    orig_factory = NumberFactory()
    patched_factory = orig_factory.frozen_patch({"result_type": int})
    assert patched_factory.result_type is int
