import logging
from typing import Any, TypedDict

import sqlalchemy
import sqlalchemy.ext.asyncio as ext_asyncio
from pydantic_core import from_json, to_json
from sqlalchemy.engine.url import make_url

_LOGGER = logging.getLogger(__name__)


class EngineKwargs(TypedDict, total=False):
    db_url: str


def create_engine[EngineT](engine_type: type[EngineT], *, db_url: str) -> EngineT:
    url = make_url(db_url)
    connect_args: dict[str, Any] = {}

    if url.drivername == "postgresql" and issubclass(engine_type, sqlalchemy.Engine):
        url = url.set(drivername="postgresql+psycopg")

    if url.drivername == "sqlite":
        # Since we use BEGIN IMMEDIATE at [1], concurrent access produces
        # SQLITE_BUSY (https://sqlite.org/rescode.html#busy) that, in turn,
        # results in a similar runtime error. We get around this by setting
        # a timeout (blocking the pending processes while the database is
        # locked).
        #
        # Note that the default timeout seems to be zero (or close to it).
        #
        # Why 120 seconds? That may seem excessive at first glance. Hopefully,
        # that is also often the case. However, it is a common practice to
        # create the database in the `on_connect` hook if it does not already
        # exist. That may be very slow.
        connect_args["timeout"] = 120  # [s]

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

    engine: sqlalchemy.Engine | ext_asyncio.AsyncEngine
    match engine_type:
        case ext_asyncio.AsyncEngine:
            engine = ext_asyncio.create_async_engine(url, **engine_kwargs)
        case sqlalchemy.Engine:
            engine = sqlalchemy.create_engine(url, **engine_kwargs)

        case _:
            raise TypeError(f"Unknown engine type '{engine_type.__name__}'")  # type: ignore[union-attr]

    if url.drivername == "sqlite":
        if not isinstance(engine, sqlalchemy.Engine):
            raise NotImplementedError
        _fix_transaction_semantics(engine)

    return engine  # type: ignore[return-value]


def _fix_transaction_semantics(db_engine: sqlalchemy.Engine) -> None:
    # See the SQLAlchemy documentation for details:
    #
    #     https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#serializable-isolation-savepoints-transactional-ddl
    #
    # Here is an excerpt from said documentation:
    #
    # > The pysqlite DBAPI driver has several long-standing bugs which impact the
    # > correctness of its transactional behavior. In its default mode of operation,
    # > SQLite features such as SERIALIZABLE isolation, transactional DDL, and
    # > SAVEPOINT support are non-functional, and in order to use these features
    # > workarounds must be taken.
    #
    @sqlalchemy.event.listens_for(db_engine, "connect")
    def do_connect(dbapi_connection: Any, _connection_record: Any) -> None:
        # disable pysqlite's emitting of the BEGIN statement entirely.
        # also stops it from emitting COMMIT before any DDL.
        dbapi_connection.isolation_level = None

    @sqlalchemy.event.listens_for(db_engine, "begin")
    def do_begin(conn: sqlalchemy.Connection) -> None:
        # emit our own BEGIN
        #
        # See: https://sqlite.org/lang_transaction.html
        #
        # Here is an excerpt:
        #
        # > IMMEDIATE causes the database connection to start a new write
        # > immediately, without waiting for a write statement. The
        # > BEGIN IMMEDIATE might fail with SQLITE_BUSY if another write
        # > transaction is already active on another database connection.
        #
        # Note that the default behaviour (BEGIN DEFERRED) seemingly does
        # not work well with concurrent database writes. At least that is
        # my (FPA) conclusion at the time of writing. Try to set it to
        # DEFERRED and see if the tests in baxter still fail with an
        # empty (uninitialized) database. Remember to run the tests in
        # parallel (e.g., `pytest -n auto`).
        conn.exec_driver_sql("BEGIN IMMEDIATE")  # [1]
