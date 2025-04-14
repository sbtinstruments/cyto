from typing import Any, TypedDict, TypeVar, Unpack, overload

import sqlalchemy.ext.asyncio as ext_asyncio
from sqlalchemy import Engine, orm


class SessionKwargs(TypedDict, total=False):
    autoflush: bool
    autobegin: bool
    close_resets_only: bool
    class_: type


_SESSION_KWARGS: SessionKwargs = {
    # `autoflush` and `autobegin` controls some if the implicit
    # "magic" that SQLAchemy does behind the scenes. We disable
    # both to avoid implicit behaviour.
    #
    # See: https://docs.sqlalchemy.org/en/20/orm/session_api.html#sqlalchemy.orm.Session.params.autoflush
    # See: https://docs.sqlalchemy.org/en/20/orm/session_api.html#sqlalchemy.orm.Session.params.autobegin
    "autoflush": False,
    "autobegin": False,
    # `close_resets_only=False``: Once you `close` the session,
    # the session is no longer reusable.
    #
    # See: https://docs.sqlalchemy.org/en/20/orm/session_api.html#sqlalchemy.orm.Session.params.close_resets_only
    "close_resets_only": False,
}

SessionT = TypeVar("SessionT", bound=orm.Session)
AsyncSessionT = TypeVar("AsyncSessionT", bound=ext_asyncio.AsyncSession)


@overload
def sessionmaker(
    bind: Engine,
    **session_kwargs: Unpack[SessionKwargs],
) -> orm.sessionmaker[orm.Session]: ...


@overload
def sessionmaker(  # type: ignore[misc]
    bind: Engine,
    *,
    class_: SessionT,
    **session_kwargs: Unpack[SessionKwargs],
) -> orm.sessionmaker[SessionT]: ...


@overload
def sessionmaker(
    bind: ext_asyncio.AsyncEngine,
    **session_kwargs: Unpack[SessionKwargs],
) -> ext_asyncio.async_sessionmaker[ext_asyncio.AsyncSession]: ...


@overload
def sessionmaker(  # type: ignore[misc]
    bind: ext_asyncio.AsyncEngine,
    *,
    class_: AsyncSessionT,
    **session_kwargs: Unpack[SessionKwargs],
) -> ext_asyncio.async_sessionmaker[AsyncSessionT]: ...


def sessionmaker(
    bind: Engine | ext_asyncio.AsyncEngine,
    **session_kwargs: Any,
) -> Any:
    session_kwargs = {
        **_SESSION_KWARGS,
        **(session_kwargs or {}),
    }
    match bind:
        case ext_asyncio.AsyncEngine():
            return ext_asyncio.async_sessionmaker(bind=bind, **session_kwargs)
        case Engine():
            return orm.sessionmaker(bind=bind, **session_kwargs)
    raise TypeError(f"Unknown engine type '{type(bind).__name__}'")
