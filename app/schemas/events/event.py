from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models import EventLevel
from app.models.event import EventSlackChannel


class EventBrief(BaseModel):
    title: str
    description: str
    level: EventLevel
    timestamp: datetime
    info: Optional[dict[str, Any]] = None
    model_config = ConfigDict(from_attributes=True)


class EventCreateIn(BaseModel):
    title: str
    description: str | None = None
    level: EventLevel
    school_id: UUID | None = None
    user_id: UUID | None = None
    info: dict[str, Any] | None = None
    slack_channel: EventSlackChannel | None = None
