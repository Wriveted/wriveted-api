from fastapi import APIRouter
from structlog import get_logger


from app.services.events import process_events

logger = get_logger()
router = APIRouter()


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

