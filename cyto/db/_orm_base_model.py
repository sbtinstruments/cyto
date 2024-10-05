from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from functools import partial
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, TypeAdapter
from sqlalchemy import JSON, TEXT, TIMESTAMP, Dialect, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass

_LOGGER = logging.getLogger(__name__)


class Base(
    DeclarativeBase,
    MappedAsDataclass,
    # Note the `kw_only=True` option:
    #
    #  * It gives us a pydantic-like interface
    #  * Enables us to declare the attributes in any order (regardless of
    #    whether they have default values or not)
    #
    kw_only=True,
):
    """Subclasses are both dataclasses and ORM models."""

    type_annotation_map: ClassVar[dict[Any, Any]] = {
        datetime: TIMESTAMP(timezone=True),
        dict[str, Any]: JSON,
        # Avoid `character varying` of various configurations (dynamic or
        # fixed length). Just use `text` for everything.
        Literal: TEXT,
        str: TEXT,
    }


# TODO: Consolidate the following with `PydanticModelAsJson` from GMDB
class PydanticJson(TypeDecorator):  # type: ignore[type-arg]
    """Map a pydantic-supported type to a JSON column."""

    impl = JSON
    cache_ok = True

    def __init__(
        self,
        # `type_` is anything supported by `pydantic.TypeAdapter`. This includes
        # special forms (e.g., `Union`s), which is why we need to use `Any` and
        # not `type[Any]` (the latter does not accept special forms).
        type_: Any,
        *,
        serialize: Callable[[Any], dict[str, Any]] | None = None,
    ) -> None:
        """Create mapping between the given model type and a JSON column."""
        # Use SQL NULL instead of JSON "null" when `value` is None.
        super().__init__(none_as_null=True)
        self._type_adapter = TypeAdapter(type_)
        if serialize is None:
            # The `warnings="error"` ensures that we get an exception should the
            # user try to assign, e.g., a raw dict as the value.
            serialize = partial(self._type_adapter.dump_python, warnings="error")
        self._serialize = serialize

    def process_bind_param(self, value: BaseModel | None, _dialect: Dialect) -> Any:
        """Convert python type to column type."""
        if value is None:
            return None
        return self._serialize(value)

    def process_result_value(self, value: Any | None, _dialect: Dialect) -> Any | None:
        """Convert column type to python type."""
        if value is None:
            return None
        # This raises if `value` is not an instance of `type_` (as given to `__init__`)
        # if we use the default serializer (with `warnings="error"`). This is a great
        # feature sinces it ensures that the user is strict about their typing.
        #
        # However, we have to set `strict=False` since we get a `dict` as value where,
        # e.g., `datetime` fields are still strings. In turn, the `strict=False` allows
        # pydantic to parse said strings.
        #
        # TODO: Parse the raw JSON instead with `validate_json`. This way, we let
        # pydantic handle all the parsing and we can avoid `strict=False`.
        return self._type_adapter.validate_python(value, strict=False)
