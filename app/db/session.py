from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Tuple

import sqlalchemy
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from sqlalchemy import URL, create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from starlette.background import BackgroundTasks
from structlog import get_logger

from app.config import Settings, get_settings

logger = get_logger()


def database_connection(
    database_uri: str | URL,
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
    SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine, future=True
    )
    return engine, SessionLocal


@lru_cache()
def get_async_session_maker(settings: Settings = None):
    if settings is None:
        settings = get_settings()

    engine = create_async_engine(
        settings.SQLALCHEMY_ASYNC_URI,
        # Pool size is the maximum number of permanent connections to keep.
        # defaults to 5
        pool_size=settings.DATABASE_POOL_SIZE,
        # Temporarily exceeds the set pool_size if no connections are available.
        # Default is 10
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
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

    SQLAlchemyInstrumentor().instrument(
        engine=engine.sync_engine, enable_commenter=True, commenter_options={}
    )

    return async_sessionmaker(
        engine, autoflush=False, autocommit=False, expire_on_commit=False
    )


@lru_cache()
def get_session_maker(settings: Settings = None):
    if settings is None:
        settings = get_settings()

    engine, SessionLocal = database_connection(
        settings.SQLALCHEMY_DATABASE_URI,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
    )
    SQLAlchemyInstrumentor().instrument(
        engine=engine,
        enable_commenter=True,
    )
    return SessionLocal


# This was introduced in https://github.com/Wriveted/wriveted-api/pull/140 to deal with a deadlock issue from
# https://github.com/tiangolo/full-stack-fastapi-postgresql/issues/104#issuecomment-775858005
# The issue has since been solved upstream so could be refactored out.
# See https://github.com/Wriveted/wriveted-api/issues/139 for a setup
class SessionManager:
    def __init__(self, session_maker: sessionmaker):
        self.session: Session = session_maker()

    def __enter__(self):
        return self.session

    def __exit__(self, exception_type, exception_value, traceback):
        self.session.close()


def close_session(session: Session):
    session.close()


def get_session(
    background_tasks: BackgroundTasks,
):
    with SessionManager(get_session_maker()) as session:
        background_tasks.add_task(close_session, session)
        try:
            yield session
        finally:
            session.close()


async def get_async_session() -> AsyncGenerator:
    logger.debug("Getting async db session")
    session_factory = get_async_session_maker()
    async with session_factory() as session:
        logger.debug("Got async db session")
        yield session
        logger.debug("Cleaning up async db session")
