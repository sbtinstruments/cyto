from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, TypeVar

from ...factory import FACTORY, CanNotProduce, ProductRegistry
from ...model import FrozenModel
from . import current_path, current_task

T = TypeVar("T")
FM = TypeVar("FM", bound=FrozenModel)


def fetch(
    type_: type[T],
    *,
    factory: ProductRegistry | None = None,
    store_produced_instance: bool | None = None,
) -> T:
    """Return the instance (if any) of the given type for the current task path.

    Automatically produces an instance of the given type if there is no existing
    instance. In this case (and if `store_produced_instance=True`), stores the
    instance for the next time around.

    Raises `RuntimeError` if there is no existing instance and we fail to produce one.
    """
    if factory is None:
        factory = FACTORY
    if store_produced_instance is None:
        store_produced_instance = True
    try:
        # Traverse the task path from the current task to the root task. Get the
        # first instance of the given type.
        instance = current_path.get_first_instance(type_)
    except LookupError:
        # If there is no instance of the given type, we attempt to produce it
        try:
            instance = factory.produce(annotation=type_)
        except CanNotProduce as exc:
            raise RuntimeError(
                f"No value for type '{type_.__name__}' for the current task and"
                " no factory could produce it."
            ) from exc
        # Remember the instance for the next time around
        if store_produced_instance:
            current_task.instances()[type_] = instance
    return instance


@contextmanager
def patch(type_: type[FM], *args: Any, **kwargs: Any) -> Iterator[FM]:
    """Patch the model for the lifetime of this context manager.

    We call `fetch` to get the original model. This means that we'll attempt
    to produce a model if there is no existing model.

    Raises `RuntimeError` if there is no existing model and we fail to produce one.
    """
    original = fetch(type_)
    try:
        patched = original.frozen_patch(*args, **kwargs)
        current_task.instances().setauto(patched)
        yield patched
    finally:
        current_task.instances().setauto(original)


@contextmanager
def override(type_: type[T], value: T) -> Iterator[T]:
    """Override the instance for the lifetime of this context manager.

    We call `fetch` to get the original instance. This means that we'll attempt
    to produce a instance if there is no existing instance.

    Raises `RuntimeError` if there is no existing instance and we fail to produce one.
    """
    original = fetch(type_)
    try:
        current_task.instances().setauto(value)
        yield value
    finally:
        current_task.instances().setauto(original)
