import sys
from typing import TypeVar

from pydantic import parse_raw_as

from ._product_registry import CanNotProduce, ProductSpec

T = TypeVar("T")


def cli_factory(spec: ProductSpec[T]) -> T:
    """Create an instance according to the given specification."""
    if spec.name is None:
        raise CanNotProduce
    # E.g., "early_bounds" --> "--early-bounds"
    cli_name = "--" + spec.name.replace("_", "-") + "="
    try:
        arg = next(arg for arg in sys.argv if arg.startswith(cli_name))
    except StopIteration as exc:
        raise CanNotProduce from exc
    cli_value = arg.removeprefix(cli_name)
    return parse_raw_as(spec.annotation, cli_value)  # type: ignore[no-any-return]
