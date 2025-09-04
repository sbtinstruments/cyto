import inspect
from collections.abc import Awaitable, Callable
from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    AsyncExitStack,
    suppress,
)
from functools import wraps
from typing import Any, Protocol

from anyio import create_task_group
from anyio.abc import TaskGroup

type Func[ReturnT] = Callable[..., Awaitable[ReturnT]]


class InjectedFunc[ReturnT](Protocol):
    """`Func` after we apply `inject` to it."""

    async def __call__(self) -> ReturnT: ...


class Factory(Protocol):
    """Given a type, return an instance of said type."""

    async def __call__(self, /, __annotation: type[Any]) -> Any: ...


async def _basic_factory(annotation: type[Any]) -> Any:
    if issubclass(annotation, TaskGroup):
        return create_task_group()
    raise ValueError


def inject[ReturnT](
    *,
    extra_factory: Factory | None = None,
) -> Callable[[Func[ReturnT]], InjectedFunc[ReturnT]]:
    """Inject instances of the given function's argument types."""

    def _inject(coro: Func[ReturnT]) -> InjectedFunc[ReturnT]:
        @wraps(coro)
        async def _wrapper() -> ReturnT:  # type: ignore[return]
            spec = inspect.getfullargspec(coro)
            args: Any = []
            async with AsyncExitStack() as stack:
                for arg_name in spec.args:
                    try:
                        annotation = spec.annotations[arg_name]
                    except KeyError as exc:
                        raise ValueError(
                            f'Argument "{arg_name} must have a type annotation"'
                        ) from exc

                    arg = await _get_arg(annotation, stack, extra_factory)
                    if arg is None:
                        raise ValueError(
                            f'Argument "{arg_name}" has unknown type '
                            f'annotation "{annotation}"'
                        )

                    if isinstance(arg, AbstractAsyncContextManager):
                        arg = await stack.enter_async_context(arg)
                    elif isinstance(arg, AbstractContextManager):
                        arg = stack.enter_context(arg)
                    args.append(arg)

                return await coro(*args)

        return _wrapper

    return _inject


async def _get_arg(
    annotation: type[Any],
    stack: AsyncExitStack,
    extra_factory: Factory | None = None,
) -> Any:
    if issubclass(annotation, AsyncExitStack):
        return stack
    with suppress(ValueError):
        return await _basic_factory(annotation)
    if extra_factory is not None:
        with suppress(ValueError):
            return await extra_factory(annotation)
    return None
