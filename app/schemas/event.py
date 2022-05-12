from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel

from app.models import EventLevel


class EventBrief(BaseModel):
    title: str
    description: str
    level: EventLevel
    timestamp: datetime
    info: Optional[dict[str, Any]]

    class Config:
        orm_mode = True


class EventCreateIn(BaseModel):
    title: str
    description: str
    level: EventLevel
    school_id: UUID | None
    info: dict[str, Any] | None
