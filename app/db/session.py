from functools import lru_cache
from typing import Tuple

import sqlalchemy
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine

from app.config import get_settings, Settings


@lru_cache()
def database_connection(database_uri: str) -> Tuple[sqlalchemy.engine.Engine, sqlalchemy.orm.sessionmaker]:
    # Ref: https://docs.sqlalchemy.org/en/13/core/pooling.html
    engine = create_engine(database_uri)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    #SQLAlchemyInstrumentor().instrument(engine=engine)

    return engine, SessionLocal


def get_session():
    settings = get_settings()
    engine, SessionMaker = database_connection(settings.SQLALCHEMY_DATABASE_URI)

    try:
        session: sqlalchemy.orm.Session = SessionMaker()
        yield session
    finally:
        session.close()

