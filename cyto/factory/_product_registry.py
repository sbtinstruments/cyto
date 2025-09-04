from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import (
    Annotated,
    Any,
    Literal,
    Protocol,
    TypeVar,
    get_args,
    get_origin,
)

_LOGGER = logging.getLogger(__name__)


T = TypeVar("T")


class ProductFactory[T](Protocol):
    """Given a produc spec, return the corresponding product."""

    def __call__(self, /, __spec: ProductSpec[T]) -> T: ...


# N818: This exception an actual error. It's a signal/sentinel.
class CanNotProduce(ValueError):  # noqa: N818
    pass


ProductSource = Literal["cli", "env", "file", "db", "default"]


@dataclass(frozen=True)
class ProductSpec[T]:
    source: ProductSource
    factory: ProductFactory[T]
    annotation: type[T] | Any = (
        Any  # Any annotation with a `type` as its first argument
    )
    name: str | None = None


class ProductRegistry:
    def __init__(self) -> None:
        self._specs: set[ProductSpec[Any]] = set()
        self._source_priorities: dict[ProductSource, int] = {
            source: index for index, source in enumerate(get_args(ProductSource))
        }

    def register_product(
        self,
        *,
        source: ProductSource,
        factory: ProductFactory[T],
        annotation: type[T] | Any = Any,
        product_name: str | None = None,
    ) -> None:
        spec: ProductSpec[Any] = ProductSpec(
            source=source,
            factory=factory,
            annotation=annotation,
            name=product_name,
        )
        self._specs.add(spec)

    def produce(
        self,
        *,
        annotation: type[T],
        name: str | None = None,
    ) -> T:
        specs = list(self._get_specs(name=name, annotation=annotation))
        specs.sort(key=lambda spec: self._source_priorities[spec.source])
        errors: list[CanNotProduce] = []
        for spec in specs:
            specific_spec = replace(spec, annotation=annotation, name=name)
            try:
                return spec.factory(specific_spec)
            except CanNotProduce as exc:
                errors.append(exc)
        raise CanNotProduce(
            f"Found no matching product spec for {annotation=} and {name=}. "
            f"Context: {errors}"
        )

    def _get_specs(
        self,
        *,
        annotation: type[T],
        name: str | None = None,
    ) -> Iterable[ProductSpec[T]]:
        for spec in self._specs:
            if not _name_matches(spec.name, name):
                continue
            if not _type_matches(spec.annotation, annotation):
                continue
            yield spec


def _name_matches(lhs: str | None, rhs: str | None) -> bool:
    if lhs is None or rhs is None:
        return True
    return lhs == rhs


def _type_matches(lhs: Any, rhs: Any) -> bool:
    try:
        lhs_type_anno = _get_type_anno(lhs)
        rhs_type_anno = _get_type_anno(rhs)
    except ValueError:
        return False
    if any(type_anno is Any for type_anno in (lhs_type_anno, rhs_type_anno)):
        return True
    return lhs_type_anno is rhs_type_anno


def _get_type_anno(anno: Any) -> Any:
    origin = get_origin(anno)
    if origin is Annotated:
        args = get_args(anno)
        # Type is always the first arg
        for arg in args:
            return arg
        raise ValueError("Annotation does not have a type")
    return anno
