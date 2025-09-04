from collections.abc import Hashable, Iterator, MutableMapping
from typing import Any


class InstanceMapping:
    """Mapping of type to an instance of said type."""

    def __init__(self, base: MutableMapping[Any, Any]) -> None:
        self._base = base

    def __getitem__[T](self, type_: type[T]) -> T:
        value = self._base[type_]
        if not isinstance(value, type_):
            raise TypeError(f"Invalid value stored for type '{type_}'")
        return value

    def __setitem__[T](self, type_: type[T], value: T) -> None:
        self._base[type_] = value

    def __delitem__(self, type_: type) -> None:
        del self._base[type_]

    def __iter__(self) -> Iterator[Hashable]:
        return iter(self._base)

    def __len__(self) -> int:
        return len(self._base)

    def setauto(self, value: Any) -> None:
        self[type(value)] = value

    def setdefault[T](self, default: T) -> T:
        type_ = type(default)
        value = self._base.setdefault(type_, default)
        if not isinstance(value, type(default)):
            raise TypeError(f"Invalid value stored for type: '{type_}'")
        return value
