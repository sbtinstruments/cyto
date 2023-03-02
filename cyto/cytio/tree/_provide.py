from contextlib import contextmanager
from inspect import Parameter
from typing import Any, Iterator, Optional, TypeVar

from ...factory import FACTORY, ArgFactory
from ...model import FrozenModel
from . import current_path, current_task

T = TypeVar("T", bound=FrozenModel)


def provide(type_: type[T], *, factory: Optional[ArgFactory] = None) -> T:
    """Get the instance of the given type for the current task path."""
    if factory is None:
        factory = FACTORY.factory
    try:
        value = current_path.get_model(type_)
    except KeyError:
        param = Parameter("_anonymous", Parameter.KEYWORD_ONLY, annotation=type_)
        try:
            value = factory(param)
        except ValueError as exc:
            raise RuntimeError(
                f"No value for type '{type_.__name__}' for the current task and"
                " no factory could produce it."
            ) from exc
        current_task.instances()[type_] = value
    if not isinstance(value, type_):
        raise RuntimeError(
            f"Invalid type '{type(value).__name__}' (expected '{type_.__name__}')"
        )
    return value


FM = TypeVar("FM", bound=FrozenModel)


@contextmanager
def patch(type_: type[FM], *args: Any, **kwargs: Any) -> Iterator[FM]:
    original = provide(type_)
    try:
        patched = original.update(*args, **kwargs)
        current_task.instances().set(patched)
        yield patched
    finally:
        current_task.instances().set(original)


@contextmanager
def override(type_: type[FM], value: FM) -> Iterator[FM]:
    original = provide(type_)
    try:
        current_task.instances().set(value)
        yield value
    finally:
        current_task.instances().set(original)
