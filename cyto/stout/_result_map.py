from collections.abc import Iterator, Mapping
from typing import Any

from pydantic import Extra, Field

from ..model import FrozenModel
from .keynote import Keynote, KeynoteTokenSeq


class ResultMap(FrozenModel, Mapping[str, Any]):
    """Basically a `dict[str, Any]` that always has a `keynote` item.

    Note that the combination of:

     * `extra = Extra.allow`
     * A default value for each field

    Makes this class *very* lenient. Basically, any map-like object coerces
    into a `ResultMap`.
    """

    # TODO: Just have a regular `keynote: Keynote` field when we get
    # pydantic v2.0 and support for custom serializers/deserializers.
    keynote_tokens: KeynoteTokenSeq = Field(KeynoteTokenSeq(), alias="keynote")

    def keynote(self) -> Keynote:
        """Return keynote parsed from the tokens."""
        return Keynote.from_token_seq(self.keynote_tokens)

    def __getitem__(self, key: str) -> Any:
        return self.__dict__[key]

    # TODO: Use the `override` decorator when we get python 3.12
    def __iter__(self) -> Iterator[str]:  # type: ignore[override]
        """Return iterator of all fields in this model.

        This includes, e.g., the "keynote" field and not just the
        extra fields given during init.
        """
        return iter(self.__dict__)

    def __len__(self) -> int:
        return len(self.__dict__)

    def __bool__(self) -> bool:
        """Has at least one item.

        The empty keynote does not count.
        """
        return bool(self.keynote()) or bool(
            {key for key in self if key != "keynote_tokens"}
        )

    # A003: We have to use `dict` since pydantic choose this name.
    def dict(self, **kwargs: Any) -> dict[str, Any]:  # noqa: A003
        # Prefer `keynote` over `keynote_tokens`. Note that we can't use `setdefault`
        # Because pydantic will override it since it uses `by_alias: bool = False` as
        # the default specification in `dict`.
        kwargs["by_alias"] = True
        return super().dict(**kwargs)

    class Config:
        # Act like a `dict[str, Any]`
        extra = Extra.allow
        # To make it easier to deal with `keynote_tokens`/`keynote`.
        allow_population_by_field_name = True
