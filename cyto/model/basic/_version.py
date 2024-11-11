from __future__ import annotations

import re
from typing import Annotated, Any, Self

from pydantic import (
    Field,
    NonNegativeInt,
    ValidatorFunctionWrapHandler,
    model_validator,
)

from .._frozen_model import FrozenModel

_COMBINED_MINOR_PATCH = re.compile(r"(?P<minor>\d+)(?P<patch>[a-z])")


class Version(FrozenModel):
    """A version number. Incompatible if major version differs.

    We use semantic versioning.

    Note that:

        repr(Version.from_string("7.4")) == "7.4.0"

    That is, we infer `patch=0` and use that in the string representation.
    """

    major: NonNegativeInt
    minor: NonNegativeInt
    patch: NonNegativeInt = 0
    modifiers: Annotated[
        tuple[str, ...], Field(examples=(("beta.0", "36", "f4323354", "dirty"),))
    ] = ()

    @model_validator(mode="wrap")
    @classmethod
    def _validate(cls, data: Any, handler: ValidatorFunctionWrapHandler) -> Any:
        if isinstance(data, str):
            return cls._from_string(data)
        return handler(data)

    @classmethod
    def _from_string(cls, raw: str) -> Self:
        """Convert raw version string to a parsed instance."""
        raw = raw.lstrip("v")  # E.g.: "v2024.03g" --> "2024.03g"
        elements = raw.split("-")
        parts: list[Any] = elements[0].split(".")
        modifiers = tuple(elements[1:])
        if not 2 <= len(parts) <= 3:  # noqa: PLR2004
            raise ValueError(
                "We only accept versions that consists of"
                " MAJOR.MINOR[.PATCH]-[MODIFIERS] (where [.PATCH] is optional). We"
                f" got: {parts}"
            )
        if len(parts) == 2:  # noqa: PLR2004
            # Special case: The patch information is encoded as a character.
            #
            # E.g.: "2024.03d" becomes: major=2024, minor=3, patch=4
            matches = _COMBINED_MINOR_PATCH.match(parts[1])
            if matches is not None:
                parts[1] = matches.group("minor")
                patch_as_char = matches.group("patch")
                assert len(patch_as_char) == 1
                patch_as_int = ord(patch_as_char) - ord("a")
                parts.append(patch_as_int)
            # Fall back: The patch is not present so we set it to zero
            else:
                parts.append(0)  # `patch` defaults to `0`
        assert len(parts) == 3  # noqa: PLR2004
        try:
            major = int(parts[0])
            minor = int(parts[1])
            patch = int(parts[2])
        except ValueError as exc:
            raise ValueError(
                f"We expect integer version numbers. We got: {parts}"
            ) from exc
        return cls(major=major, minor=minor, patch=patch, modifiers=modifiers)

    def is_beta(self) -> bool:
        """Is this a "beta" (e.g., not "stable") release."""
        return any(mod.startswith("beta") for mod in self.modifiers)

    def __repr__(self) -> str:
        """Return string representation of this version."""
        mod_suffix = "-" + "-".join(self.modifiers) if self.modifiers else ""
        return f"{self.major}.{self.minor}.{self.patch}{mod_suffix}"

    def __ge__(self, rhs: Version) -> bool:
        """Is this version greater than or equal to the given version.

        Does a pairwise comparison of the version components.
        """
        # TODO: Also take the modifiers into account.
        return (self.major, self.minor, self.patch) >= (rhs.major, rhs.minor, rhs.patch)


VersionField = Annotated[
    Version,
    # ruff: noqa: ERA001
    #
    # Allows us to specify default values using, e.g., strings. Example:
    #
    #     class SystemInfo(BaseModel):
    #         software_ver: Version = "2024.03a"
    #         hardware_ver: Version = "1.0"
    #
    Field(validate_default=True),
]
