from fastapi import APIRouter, Security
from pydantic import BaseSettings, BaseModel
from structlog import get_logger

from app.api.dependencies.security import get_current_active_user_or_service_account
from app.services.events import process_events


class CloudRunEnvironment(BaseSettings):
    K_SERVICE: str = None
    K_REVISION: str = None
    K_CONFIGURATION: str = None


cloud_run_config = CloudRunEnvironment()

logger = get_logger()

router = APIRouter()


@router.get("/version")
async def get_version():
    cloud_run_revision = cloud_run_config.K_REVISION or "Unknown"
    return {"cloud_run_revision": cloud_run_revision, "version": "internal"}


class ProcessEventPayload(BaseModel):
    event_id: str


@router.post("/process-event")
async def process_event(data: ProcessEventPayload):
    return process_events(
        event_id=data.event_id,
    )
