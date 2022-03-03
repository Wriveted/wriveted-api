from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, UUID4

from app.models import ServiceAccountType
from app.schemas.event import EventBrief
from app.schemas.school import SchoolIdentity, SchoolWrivetedIdentity


class ServiceAccountBrief(BaseModel):
    id: UUID4
    name: str
    type: ServiceAccountType
    is_active: bool

    class Config:
        orm_mode = True


class ServiceAccountDetail(ServiceAccountBrief):
    info: Optional[dict]
    created_at: datetime
    updated_at: datetime
    events: List[EventBrief]
    schools: List[SchoolIdentity]


class ServiceAccountCreatedResponse(ServiceAccountBrief):
    access_token: str


class ServiceAccountCreateIn(BaseModel):
    name: str
    type: ServiceAccountType
    info: Optional[dict]
    schools: Optional[List[SchoolWrivetedIdentity]]


class ServiceAccountUpdateIn(BaseModel):
    name: Optional[str]
    info: Optional[dict]
    schools: Optional[List[SchoolWrivetedIdentity]]
