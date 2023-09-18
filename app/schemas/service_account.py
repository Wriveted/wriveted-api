from datetime import datetime
from typing import List, Optional

from pydantic import UUID4, BaseModel, ConfigDict, field_validator
from sqlalchemy.orm.dynamic import AppenderQuery

from app.models import ServiceAccountType
from app.schemas.events.event import EventBrief
from app.schemas.school_identity import SchoolIdentity, SchoolWrivetedIdentity


class ServiceAccountBrief(BaseModel):
    id: UUID4
    name: str
    type: ServiceAccountType
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class ServiceAccountDetail(ServiceAccountBrief):
    info: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    events: List[EventBrief]
    schools: List[SchoolIdentity]

    @field_validator("events", mode="before")
    @classmethod
    def limit_events(cls, v):
        return v[:10] if isinstance(v, AppenderQuery) else v


class ServiceAccountCreatedResponse(ServiceAccountBrief):
    access_token: str


class ServiceAccountCreateIn(BaseModel):
    name: str
    type: ServiceAccountType
    info: Optional[dict] = None
    schools: Optional[List[SchoolWrivetedIdentity]] = None


class ServiceAccountUpdateIn(BaseModel):
    name: Optional[str] = None
    info: Optional[dict] = None
    schools: Optional[List[SchoolWrivetedIdentity]] = None
