from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Self, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


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

    def apply(self, model: T) -> T:
        """Apply the given patch and return the result.

        Does *not* validate the model. Uses `model_copy(update=...)` underneath,
        which applies no validation whatsoever.
        """
        fields = self.path.split(".")
        return self._apply(model, fields=fields)

    def _apply(self, model: T, *, fields: list[str]) -> T:
        first_field, rest = fields[0], fields[1:]

        # Give a nice error message if the field is not present in the model
        if first_field not in model.model_fields:
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

    def apply(self, model: T, *, validation: ValidationMode | None = None) -> T:
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
            validated_model = model.__pydantic_validator__.validate_python(
                model.model_dump(
                    # We know that some fields may be invalid (which also causes
                    # serialization warnings) but that's the entire point.
                    # The `validate_python` raises the proper ValidationError.
                    # Therefore, we can safely disable the serialization warnings.
                    warnings="none",
                )
            )
            if validation == "full":
                model = validated_model

        return model
