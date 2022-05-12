from datetime import datetime
from typing import Any, Optional
from uuid import UUID
from pydantic import AnyHttpUrl, BaseModel, constr
from app.models import SchoolState
from app.models.school import SchoolBookbotType
from app.schemas.country import CountryDetail
from app.schemas.user import UserBrief


class SchoolLocation(BaseModel):
    suburb: Optional[str]
    state: str
    postcode: str
    geolocation: Optional[str]
    lat: Optional[str]
    long: Optional[str]


class SchoolInfo(BaseModel):
    location: SchoolLocation
    type: Optional[str]
    sector: Optional[str]
    URL: Optional[str]
    status: Optional[str]
    age_id: Optional[str]
    experiments: Optional[dict[str, bool]]


class SchoolWrivetedIdentity(BaseModel):
    wriveted_identifier: UUID
    name: str

    class Config:
        orm_mode = True


class SchoolIdentity(SchoolWrivetedIdentity):
    official_identifier: Optional[str]
    country_code: str


class SchoolSelectorOption(SchoolIdentity):
    name: str
    info: SchoolInfo
    state: Optional[SchoolState]

    collection_count: Optional[int]
    admin: Optional[UserBrief]

    class Config:
        orm_mode = True


class SchoolBrief(SchoolIdentity):
    name: str
    state: SchoolState
    collection_count: int


class SchoolBookbotInfo(BaseModel):
    wriveted_identifier: UUID
    name: str
    state: SchoolState
    bookbot_type: SchoolBookbotType

    class Config:
        orm_mode = True


class SchoolDetail(SchoolBrief):
    country: CountryDetail
    info: Optional[SchoolInfo]

    admin: Optional[UserBrief]
    lms_type: str

    created_at: datetime
    updated_at: datetime

    student_domain: Optional[AnyHttpUrl]
    teacher_domain: Optional[AnyHttpUrl]


class SchoolCreateIn(BaseModel):
    name: str
    country_code: constr(min_length=3, max_length=3)
    official_identifier: Optional[str]
    lms_type: Optional[str]
    info: SchoolInfo
    student_domain: Optional[AnyHttpUrl]
    teacher_domain: Optional[AnyHttpUrl]


# Note can't change the country code or official identifier
class SchoolUpdateIn(BaseModel):
    name: Optional[str]
    info: Optional[Any]
    student_domain: Optional[AnyHttpUrl]
    teacher_domain: Optional[AnyHttpUrl]


class SchoolPatchOptions(BaseModel):
    status: Optional[SchoolState]
    bookbot_type: Optional[SchoolBookbotType]
    lms_type: Optional[str]
