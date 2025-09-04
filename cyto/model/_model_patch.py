from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Self

from pydantic import BaseModel


class PatchError(ValueError):
    pass


@dataclass(frozen=True, kw_only=True)
class AssignOp:
    value: Any


StitchOp = AssignOp

ValidationMode = Literal[
    "full",
    "none",
    "immutable",
]


@dataclass(frozen=True, kw_only=True)
class Stitch:
    path: str
    operation: StitchOp

    @classmethod
    def from_item(cls, item: tuple[str, Any]) -> Self:
        path, value = item
        return cls(path=path, operation=AssignOp(value=value))

    def apply[T: BaseModel](self, model: T) -> T:
        """Apply the given patch and return the result.

        Does *not* validate the model. Uses `model_copy(update=...)` underneath,
        which applies no validation whatsoever.
        """
        fields = self.path.split(".")
        return self._apply(model, fields=fields)

    def _apply[T: BaseModel](self, model: T, *, fields: list[str]) -> T:
        first_field, rest = fields[0], fields[1:]

        # Give a nice error message if the field is not present in the model
        if first_field not in type(model).model_fields:
            raise PatchError(
                f"{type(model).__name__} does not have the '{first_field}' field"
            )

        # Base case
        if not rest:
            assert isinstance(self.operation, AssignOp)
            return model.model_copy(update={first_field: self.operation.value})

        # Recursive case
        child_model = getattr(model, first_field)
        if not isinstance(child_model, BaseModel):
            raise PatchError(
                f"The {type(model).__name__}.{first_field} field is not a "
                "BaseModel instance"
            )
        return model.model_copy(
            update={first_field: self._apply(child_model, fields=rest)}
        )


@dataclass(frozen=True, kw_only=True)
class Patch:
    stitches: tuple[Stitch, ...]

    @classmethod
    def from_dict(cls, dict_patch: dict[str, Any]) -> Self:
        stitches = (Stitch.from_item(item) for item in dict_patch.items())
        return cls(stitches=tuple(stitches))

    def apply[T: BaseModel](
        self, model: T, *, validation: ValidationMode | None = None
    ) -> T:
        """Apply this patch on the given model.

        See the docstring for `FrozenModel.frozen_patch` for details about
        the various options.
        """
        if validation is None:
            validation = "full"

        for stitch in self.stitches:
            model = stitch.apply(model)

        # The `stitch.apply` method does not validate the result. Therefore,
        # we (optionally) validate the resulting model here.
        if validation != "none":
            # Note that `model.model_validate(model)` only works when
            # `revalidate_instances="always"`. See the `FrozenModel` class
            # for details.
            validated_model = model.model_validate(model)
            if validation == "full":
                model = validated_model

        return model
