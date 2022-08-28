import platform
from functools import lru_cache
from importlib import metadata
from importlib.metadata import PackageNotFoundError
from textwrap import dedent

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.responses import Response

from alembic.runtime.migration import MigrationContext
from app.db.session import get_session


class Version(BaseModel):
    version: str
    python_version: str
    database_revision: str


router = APIRouter()


@lru_cache()
def get_db_revision(db: Session):
    with db as session:
        connection = session.connection()
        database_context = MigrationContext.configure(connection)
        current_db_rev = database_context.get_current_revision()

    if current_db_rev is None:
        current_db_rev = "development"
    return current_db_rev


@router.get("/version", response_model=Version)
async def get_version(db: Session = Depends(get_session)):
    try:
        application_version = metadata.version("wriveted-api")
    except PackageNotFoundError:
        application_version = "unknown"
    return {
        "version": application_version,
        "python_version": platform.python_version(),
        "database_revision": get_db_revision(db),
    }


@router.get("/.well-known/security.txt")
async def get_security_policy():
    data = dedent(
        """
    Contact: mailto:security@wriveted.com
    Expires: 2025-12-31T11:00:00.000Z
    Preferred-Languages: en
    """
    )
    return Response(content=data, media_type="text/plain")
