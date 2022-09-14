import platform
from importlib import metadata
from importlib.metadata import PackageNotFoundError
from textwrap import dedent

from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel, BaseSettings
from sqlalchemy.orm import Session
from starlette.responses import Response

from alembic.runtime.migration import MigrationContext
from app.db.session import get_session

from structlog import get_logger
from app import crud
from time import sleep
from app.db.session import get_session_maker


class CloudRunEnvironment(BaseSettings):
    K_SERVICE: str = None
    K_REVISION: str = None
    K_CONFIGURATION: str = None


class Version(BaseModel):
    version: str
    python_version: str
    database_revision: str
    cloud_run_revision: str


cloud_run_config = CloudRunEnvironment()

router = APIRouter()
logger = get_logger()


def test_background_task():
    logger.info("BACKGROUND: about to create session")
    Session = get_session_maker()
    with Session() as session:
        logger.info("=== BACKGROUND: RUNNING (with session) ===")
        sleep(10)
        crud.event.create(session, title="BACKGROUND: CREATED AN EVENT")
        logger.info("=== BACKGROUND: COMPLETE ===")


@router.get("/testbg")
async def test_bg_task(background_tasks: BackgroundTasks):
    logger.info("About to trigger a background task...")
    background_tasks.add_task(test_background_task)

    return {
        "msg": "Good luck",
        "events": "https://wriveted-api--pr24-test-bg-m407wge8.web.app/events",
        "logs": "https://console.cloud.google.com/logs/query;query=resource.type%3D%22cloud_run_revision%22%0Aresource.labels.service_name%3D%22wriveted-api-development%22;timeRange=2022-09-14T01:00:40.735Z%2F;cursorTimestamp=2022-09-14T01:08:00.821883Z?referrer=search&project=wriveted-api",
    }


@router.get("/version", response_model=Version)
async def get_version(session: Session = Depends(get_session)):
    database_context = MigrationContext.configure(session.connection())
    current_db_rev = database_context.get_current_revision()

    if current_db_rev is None:
        current_db_rev = "development"

    try:
        application_version = metadata.version("wriveted-api")
    except PackageNotFoundError:
        application_version = "unknown"

    cloud_run_revision = cloud_run_config.K_REVISION or "Unknown"

    return {
        "version": application_version,
        "python_version": platform.python_version(),
        "database_revision": current_db_rev,
        "cloud_run_revision": cloud_run_revision,
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
