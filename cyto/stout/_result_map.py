from collections.abc import Iterator, Mapping
from typing import Any

from pydantic import Extra

from ..model import FrozenModel
from .keynote._keynote import Keynote


class ResultMap(FrozenModel, Mapping[str, Any]):
    """Basically a `dict[str, Any]` that always has a `keynote` item.

    Note that the combination of:

     * `extra = Extra.allow`
     * A default value for each field

    Makes this class *very* lenient. Basically, any map-like object coerces
    into a `ResultMap`.
    """

    keynote: Keynote = Keynote()

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
        return bool(self.keynote) or bool({key for key in self if key != "keynote"})

    class Config:
        # Act like a `dict[str, Any]`
        extra = Extra.allow
