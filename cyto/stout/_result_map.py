from collections.abc import Iterator, Mapping
from typing import Any, ClassVar, override

from pydantic import ConfigDict, Field

from ..model import FrozenModel
from .keynote import Keynote, KeynoteTokenSeq


class ResultMap(FrozenModel, Mapping[str, Any]):
    """Basically a `dict[str, Any]` that always has a `keynote` item.

    Note that the combination of:

     * `extra = "allow"`
     * A default value for each field

    Makes this class *very* lenient. Basically, any map-like object coerces
    into a `ResultMap`.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        # Act like a `dict[str, Any]`
        extra="allow",
    )

    keynote: Keynote = Keynote()

    def __getitem__(self, key: str) -> Any:
        assert self.__pydantic_extra__ is not None
        return self.__pydantic_extra__[key]

    @override
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
        return bool(self.keynote) or bool(self.__pydantic_extra__)
