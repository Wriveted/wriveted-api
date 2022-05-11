from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.models import EventLevel
from app.schemas.school import SchoolWrivetedIdentity
from app.schemas.service_account import ServiceAccountBrief
from app.schemas.user import UserIdentity


class EventBrief(BaseModel):
    title: str
    description: str
    level: EventLevel
    timestamp: datetime
    info: Optional[dict[str, Any]]

    class Config:
        orm_mode = True
        

class EventDetail(EventBrief):
    school: Optional[SchoolWrivetedIdentity]
    user: UserIdentity | None
    service_account: ServiceAccountBrief | None
        

class EventCreateIn(BaseModel):
    title: str
    description: str
    level: EventLevel
    school_id: Optional[str]
    info: Optional[dict[str, Any]] 