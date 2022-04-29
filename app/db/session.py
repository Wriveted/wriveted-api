from functools import lru_cache
from typing import Optional, Tuple

import sqlalchemy
from fastapi import Depends
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings, get_settings


@lru_cache()
def database_connection(
    database_uri: str,
) -> Tuple[sqlalchemy.engine.Engine, sqlalchemy.orm.sessionmaker]:
    # Ref: https://docs.sqlalchemy.org/en/14/core/pooling.html
    engine = create_engine(
        database_uri,
        # Pool size is the maximum number of permanent connections to keep.
        # defaults to 5
        # pool_size=5,
        # Temporarily exceeds the set pool_size if no connections are available.
        # Default is 10
        max_overflow=2,
        # 'pool_recycle' is the maximum number of seconds a connection can persist.
        # Connections that live longer than the specified amount of time will be
        # reestablished on checkout.
        # https://docs.sqlalchemy.org/en/14/core/pooling.html#setting-pool-recycle
        pool_recycle=900,  # 15 minutes,
        # 'pool_timeout' is the maximum number of seconds to wait when retrieving a
        # new connection from the pool. After the specified amount of time, an
        # exception will be thrown.
        pool_timeout=30,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    return engine, SessionLocal


def get_session(settings: Optional[Settings] = Depends(get_settings)):
    if settings is None:
        settings = get_settings()

    engine, SessionMaker = database_connection(settings.SQLALCHEMY_DATABASE_URI)

    try:
        session: sqlalchemy.orm.Session = SessionMaker()
        yield session
    finally:
        session.close()
