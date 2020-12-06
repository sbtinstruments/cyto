import inspect
from contextlib import AsyncExitStack, suppress
from functools import wraps
from typing import (
    Any,
    AsyncContextManager,
    Callable,
    ContextManager,
    Coroutine,
    Optional,
    Protocol,
    Type,
    TypeVar,
)

from anyio import create_task_group
from anyio.abc import TaskGroup

ReturnT = TypeVar("ReturnT", covariant=True)

Func = Callable[..., Coroutine[Any, Any, ReturnT]]


# Note that we disable D102 for `Protocol`s since it's redundant documentation.
# Similarly, we disable too-few-public-methods since it doens't make sense for
# `Protocol`s. Hopefully, both pydocstyle and pylint will special-case `Protocol`s
# soon enough.


class InjectedFunc(Protocol[ReturnT]):  # pylint: disable=too-few-public-methods
    """`Func` after we apply `inject` to it."""

    async def __call__(self) -> ReturnT:  # noqa: D102
        ...


class Factory(Protocol):  # pylint: disable=too-few-public-methods
    """Given a type, return an instance of said type."""

    async def __call__(self, __annotation: Type[Any]) -> Any:  # noqa: D102
        ...


async def _basic_factory(annotation: Type[Any]) -> Any:
    if issubclass(annotation, TaskGroup):
        return create_task_group()
    raise ValueError


def inject(
    *,
    extra_factory: Optional[Factory] = None,
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

                    # There is a bug in pylint with
                    # isinstance-second-argument-not-valid-type
                    # See: https://github.com/PyCQA/pylint/issues/3507
                    if isinstance(  # pylint: disable=isinstance-second-argument-not-valid-type
                        arg, AsyncContextManager
                    ):
                        arg = await stack.enter_async_context(arg)
                    elif isinstance(  # pylint: disable=isinstance-second-argument-not-valid-type
                        arg, ContextManager
                    ):
                        arg = stack.enter_context(arg)
                    args.append(arg)

                return await coro(*args)

        return _wrapper

    return _inject


async def _get_arg(
    annotation: Type[Any],
    stack: AsyncExitStack,
    extra_factory: Optional[Factory] = None,
) -> Any:
    if issubclass(annotation, AsyncExitStack):
        return stack
    with suppress(ValueError):
        return await _basic_factory(annotation)
    if extra_factory is not None:
        with suppress(ValueError):
            return await extra_factory(annotation)
    return None
