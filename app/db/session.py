from functools import lru_cache
from typing import Tuple

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from structlog import get_logger

from app.config import Settings, get_settings

logger = get_logger()


def database_connection(
    database_uri: str,
    pool_size=10,
    max_overflow=10,
) -> Tuple[sqlalchemy.engine.Engine, sqlalchemy.orm.sessionmaker]:
    # Ref: https://docs.sqlalchemy.org/en/14/core/pooling.html
    """
    Note Cloud SQL instance has a limited number of connections:
    Currently: 50 in non-prod and 100 in prod.

    The settings here need to be considered along with concurrency settings in
    Cloud Run - how many containers will be brought up, and how many requests
    can they each serve.
    """
    engine = create_engine(
        database_uri,
        # Pool size is the maximum number of permanent connections to keep.
        # defaults to 5
        pool_size=pool_size,
        # Temporarily exceeds the set pool_size if no connections are available.
        # Default is 10
        max_overflow=max_overflow,
        # 'pool_recycle' is the maximum number of seconds a connection can persist.
        # Connections that live longer than the specified amount of time will be
        # reestablished on checkout.
        # https://docs.sqlalchemy.org/en/14/core/pooling.html#setting-pool-recycle
        pool_recycle=900,  # 15 minutes,
        # 'pool_timeout' is the maximum number of seconds to wait when retrieving a
        # new connection from the pool. After the specified amount of time, an
        # exception will be thrown.
        pool_timeout=120,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal


@lru_cache()
def get_session_maker(settings: Settings = None):
    if settings is None:
        settings = get_settings()

    engine, SessionLocal = database_connection(
        settings.SQLALCHEMY_DATABASE_URI,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
    )
    return SessionLocal


def get_session():
    session_maker = get_session_maker()
    session: sqlalchemy.orm.Session = session_maker()
    try:
        yield session
    finally:
        session.close()
