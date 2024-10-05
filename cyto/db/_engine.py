import logging
from typing import Any, TypeVar

import sqlalchemy
import sqlalchemy.ext.asyncio as ext_asyncio
from pydantic_core import from_json, to_json
from sqlalchemy.engine.url import make_url

_LOGGER = logging.getLogger(__name__)

EngineT = TypeVar("EngineT", bound=type)


def create_engine(engine_type: type[EngineT], *, db_url: str) -> EngineT:
    url = make_url(db_url)
    connect_args: dict[str, Any] = {}

    if url.drivername == "postgresql" and issubclass(engine_type, sqlalchemy.Engine):
        url = url.set(drivername="postgresql+psycopg")

    # Unfortunately, SQLAlchemy does not provide a direct way to specify,
    # which *database driver* that we want (e.g., `psycopg2` or `asyncpg`).
    # The only way to do so is to via the connection URL. Therefore, we have
    # to manually augment the URL to choose the driver.
    if url.drivername == "postgresql" and issubclass(
        engine_type, ext_asyncio.AsyncEngine
    ):
        url = url.set(drivername="postgresql+asyncpg")

        # There is a compatibility bug with how to specify SSL settings between
        # SQLAlchemy and asyncpg.
        #
        # See: https://github.com/MagicStack/asyncpg/issues/737
        if sslmode := url.query.get("sslmode"):
            # Remove "sslmode" from the URL
            url = url.difference_update_query(["sslmode"])
            # Add "ssl" to the connection arguments that go directly to
            # the asyncpg driver.
            connect_args["ssl"] = sslmode

    engine_kwargs = {
        "connect_args": connect_args,
        # Use pydantic's JSON serializer/deserializer. This adds support for, e.g.,
        # `datetime` objects.
        "json_serializer": lambda val: to_json(val).decode("utf-8"),
        "json_deserializer": lambda val: from_json(val),
    }

    match engine_type:
        case ext_asyncio.AsyncEngine:
            return ext_asyncio.create_async_engine(url, **engine_kwargs)
        case sqlalchemy.Engine:
            return sqlalchemy.create_engine(url, **engine_kwargs)
    raise TypeError(f"Unknown engine type '{engine_type.__name__}'")
