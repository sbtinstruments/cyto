from __future__ import annotations

from inspect import Parameter
from typing import Any, Callable, Coroutine, Optional, Protocol, TypeVar

R = TypeVar("R")
Coro = Callable[..., Coroutine[Any, Any, R]]

# Note that we disable D102 for `Protocol`s since it's redundant documentation.
# Similarly, we disable too-few-public-methods since it doens't make sense for
# `Protocol`s. Hopefully, both pydocstyle and pylint will special-case `Protocol`s
# soon enough.


class ArgFactory(Protocol):  # pylint: disable=too-few-public-methods
    """Given a parameter, return a corresponding argument."""

    def __call__(self, __param: Parameter) -> Any:  # noqa: D102
        ...


class ArgFactoryGroup:
    def __init__(self) -> None:
        self._factories: list[ArgFactory] = []

    def add_factory(self, arg_factory: ArgFactory) -> None:
        self._factories.append(arg_factory)

    def generate_factory(
        self,
        *,
        name: Optional[str] = None,
        type_: Any,
        arg: Any,
    ) -> None:
        async def _factory(param: Parameter) -> Any:
            if type_ is not None and param.annotation is not type_:
                raise ValueError
            if name is not None and param.name is not name:
                raise ValueError
            return arg

        self.add_factory(_factory)

    def factory(self, param: Parameter) -> Any:
        for factory in self._factories:
            try:
                return factory(param)
            except ValueError:
                pass
        raise ValueError(f"No factory could produce a value for {param}")
