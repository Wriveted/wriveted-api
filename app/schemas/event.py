from datetime import datetime

from pydantic import BaseModel

from app.models import EventLevel


class EventBrief(BaseModel):
    title: str
    description: str
    level: EventLevel
    timestamp: datetime

    class Config:
        orm_mode = True
