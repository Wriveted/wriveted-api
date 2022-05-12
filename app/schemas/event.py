from datetime import datetime
from typing import Any, Optional

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
    school_id: Optional[str]
    info: Optional[dict[str, Any]] 