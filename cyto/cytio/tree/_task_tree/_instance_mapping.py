from typing import Any, Hashable, Iterator, MutableMapping, TypeVar

T = TypeVar("T")


class InstanceMapping:
    """Mapping of type to an instance of said type."""

    def __init__(self, base: MutableMapping[Any, Any]) -> None:
        self._base = base

    def __getitem__(self, type_: type[T]) -> T:
        value = self._base[type_]
        if not isinstance(value, type_):
            raise RuntimeError(f"Invalid value stored for type '{type_}'")
        return value

    def __setitem__(self, type_: type[T], value: T) -> None:
        self._base[type_] = value

    def __delitem__(self, type_: type) -> None:
        del self._base[type_]

    def __iter__(self) -> Iterator[Hashable]:
        return iter(self._base)

    def __len__(self) -> int:
        return len(self._base)

    def set(self, value: Any) -> None:
        self[type(value)] = value

    def setdefault(self, default: T) -> T:
        type_ = type(default)
        value = self._base.setdefault(type_, default)
        if not isinstance(value, type(default)):
            raise RuntimeError(f"Invalid value stored for type: '{type_}'")
        return value
