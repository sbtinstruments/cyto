from __future__ import annotations

import re
from typing import Annotated, Any, Self, override

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
    raw: Annotated[str | None, Field(exclude=True)] = None
    """Used to remember the original representation.

    This ensures that we return a character-by-character accurate in
    the __repr__ function.
    """

    @model_validator(mode="wrap")
    @classmethod
    def _validate(cls, data: Any, handler: ValidatorFunctionWrapHandler) -> Any:
        if isinstance(data, str):
            return cls._from_string(data)
        return handler(data)

    @classmethod
    def _from_string(cls, raw: str) -> Self:
        """Convert raw version string to a parsed instance."""
        stripped = raw.lstrip("v")  # E.g.: "v2024.03g" --> "2024.03g"
        elements = stripped.split("-")
        parts: list[Any] = elements[0].split(".")
        modifiers = tuple(elements[1:])
        if not 2 <= len(parts) <= 3:
            raise ValueError(
                "We only accept versions that consists of"
                " MAJOR.MINOR[.PATCH]-[MODIFIERS] (where [.PATCH] is optional). We"
                f" got: {parts}"
            )
        if len(parts) == 2:
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
        assert len(parts) == 3
        try:
            major = int(parts[0])
            minor = int(parts[1])
            patch = int(parts[2])
        except ValueError as exc:
            raise ValueError(
                f"We expect integer version numbers. We got: {parts}"
            ) from exc
        return cls(major=major, minor=minor, patch=patch, modifiers=modifiers, raw=raw)

    def is_beta(self) -> bool:
        """Is this a "beta" (e.g., not "stable") release."""
        return any(mod.startswith("beta") for mod in self.modifiers)

    def __repr__(self) -> str:
        """Return string representation of this version."""
        if self.raw is not None:
            return self.raw
        mod_suffix = "-" + "-".join(self.modifiers) if self.modifiers else ""
        return f"{self.major}.{self.minor}.{self.patch}{mod_suffix}"

    @override
    def __eq__(self, rhs: object) -> bool:
        """Is this version equal to the given version.

        Does a pairwise comparison of the version components (including modifiers).

        Per design, this does _not_ test that the original (raw) form of the
        version is the same. In other words:

         * "1.0" equals "1.0.0"
         * "v7.5a" equals "7.5.0"
         * "1989.08-dirty-beta" equals "1989.8.0-dirty-beta"

        """
        if not isinstance(rhs, Version):
            return NotImplemented
        return (
            self.major,
            self.minor,
            self.patch,
            self.modifiers,
        ) == (
            rhs.major,
            rhs.minor,
            rhs.patch,
            rhs.modifiers,
        )

    def __ge__(self, rhs: object) -> bool:
        """Is this version greater than or equal to the given version.

        Does a pairwise comparison of the version components.
        """
        if not isinstance(rhs, Version):
            return NotImplemented
        # TODO: Also take the modifiers into account.
        return (self.major, self.minor, self.patch) >= (rhs.major, rhs.minor, rhs.patch)

    def __hash__(self) -> int:
        return super().__hash__()


VersionField = Annotated[
    Version,
    #
    # Allows us to specify default values using, e.g., strings. Example:
    #
    #     class SystemInfo(BaseModel):
    #         software_ver: Version = "2024.03a"
    #         hardware_ver: Version = "1.0"
    #
    Field(validate_default=True),
]
