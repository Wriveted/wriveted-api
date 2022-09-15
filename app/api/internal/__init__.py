from fastapi import APIRouter, Security
from structlog import get_logger

from app.api.dependencies.security import get_current_active_user_or_service_account
from app.services.events import process_events

logger = get_logger()
router = APIRouter(dependencies=[
    Security(get_current_active_user_or_service_account)
])


@router.get("/version")
async def get_version():
    return {
        "version": "internal"
    }


@router.post("/process-event")
async def process_event(event_id: str):
    return process_events(
        event_id=event_id,
    )

