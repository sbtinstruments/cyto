from typing import Any, TypedDict, TypeVar

import sqlalchemy.ext.asyncio as ext_asyncio
from sqlalchemy import Engine, orm

from ._engine import create_engine


class SessionKwargs(TypedDict):
    autoflush: bool
    autobegin: bool
    close_resets_only: bool


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

SessionT = TypeVar("SessionT", bound=type)


def sessionmaker(
    session_type: type[SessionT], *, db_url: str, **kwargs: Any
) -> SessionT:
    session_kwargs = {**_SESSION_KWARGS, **kwargs}
    match session_type:
        case ext_asyncio.AsyncSession:
            db_engine = create_engine(ext_asyncio.AsyncEngine, db_url=db_url)
            return ext_asyncio.async_sessionmaker(bind=db_engine, **session_kwargs)
        case orm.Session:
            db_engine = create_engine(Engine, db_url=db_url)
            return orm.sessionmaker(bind=db_engine, **session_kwargs)
    raise TypeError(f"Unknown session type '{session_type.__name__}'")
