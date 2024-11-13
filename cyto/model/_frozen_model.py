from __future__ import annotations

from typing import Any, ClassVar, Self, TypeVar

from pydantic import BaseModel, ConfigDict

from ._model_patch import Patch, ValidationMode

Derived = TypeVar("Derived", bound=BaseModel)


class FrozenModel(BaseModel):
    """Immutable model."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True,
        # `extra="forbid"` is not strictly necessary for immutability but it's a sound
        # default. It adds another layer of "strictness" that we expect in the context
        # of immutability.
        extra="forbid",
        # In `frozen_patch`, we want to validate the result. To do so, we use
        # this trick: `model.model_validate(model)`. However,
        # this trick only works if we also set `revalidate_instances="always"`.
        #
        # See the pydantic documentation for details:
        # https://docs.pydantic.dev/latest/concepts/models/#error-handling
        revalidate_instances="always",
    )

    # TODO: Add model validator that ensure that all members are frozen as well

    def frozen_patch(
        self,
        patch: dict[str, Any],
        *,
        validation: ValidationMode | None = None,
    ) -> Self:
        """Return copy with the patch applied.

        Just like with `BaseModel.model_copy(update=...)`, we face the non-trivial
        problem of how to validate the result. Note that `model_copy` chose
        to simply *not validate at all*.

        Unfortunately, there is no "one size fits all" way to validate the result.
        Therefore, we offer the `validation` parameter that allows the user to chose
        the behaviour:

        | `validation` | Raises ValidationError? | Applies validation mutation? |
        |--------------|-------------------------|------------------------------|
        | "full"       | Yes                     | Yes                          |
        | "none"       | No                      | No                           |
        | "immutable"  | Yes                     | No                           |

        It's tricky to choose the right `validation`. Here is a more detailed
        explanation of each setting:

         * "full" (**default**): We esentially reconstruct the entire
           model from scratch (with the patch applied). This applies the
           validation logic *to each and every field* of the model (including
           submodels).
         * "none": We don't validate the model at all. You should
           trust the data given in `patch`. This is just like
           `model_copy(update=...)`. In fact, "none" just performs
           a series of `model_copy`s under the hood.
         * "immutable": This is in between "full"
           and "none". We reconstruct the model (which may raise
           `ValidationError`) but then we discard the reconstruction.
           The returned model is the same as for "none".


        ## Mutating validators and `validation="full"`

        Pydantic allows a validator to change the stored value. This can lead to
        surprising behaviour. Here is a simple example:

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

        Note how `my_square` is suddenly squared again even though we didn't
        patch it directly! This is because we reconstruct the model that, in turn,
        applies the `Squared` validator on the value 9 (resulting in 81).

        If we use "immutable", this does not occur:

            patched_model = my_model.frozen_patch({"my_int": 7}, validation="immutable")
            assert patched_model.my_int == 7
            assert patched_model.my_square == 9  # 3 squared

        Which `validation` is the right one? That depends on your use case. It gets even
        more complicated if you have `model_validator`s that mutate the result.

        ## Note on naming

        Pydantic v2 prefixes (most of) their models/fields with `model_`. E.g.,
        `model_copy`, `model_validate_json`, `model_fields`, etc.

        We (cyto team) opt to do the same but use the `frozen_` prefix instead.
        This way, it's easy for the user to distinguish between what comes from
        Pydantic's `BaseModel` and what comes from cyto's `FrozenModel`.
        """
        canonical_patch = Patch.from_dict(patch)
        return canonical_patch.apply(self, validation=validation)
