from uuid import UUID
from typing import Optional, Any, List

from pydantic import BaseModel, AnyHttpUrl, constr

from app.models import SchoolState
from app.schemas.country import CountryDetail


class SchoolLocation(BaseModel):
    suburb: str
    state: str
    postcode: str
    geolocation: Optional[str]
    lat: Optional[str]
    long: Optional[str]


class SchoolInfo(BaseModel):
    location: SchoolLocation
    type: Optional[str]
    sector: Optional[str]
    status: Optional[str]
    age_id: Optional[str]


class SchoolIdentity(BaseModel):
    official_identifier: str
    country_code: str
    wriveted_identifier: UUID

    class Config:
        orm_mode = True


class SchoolSelectorOption(SchoolIdentity):
    name: str
    info: SchoolInfo
    state: Optional[SchoolState]

    class Config:
        orm_mode = True


class SchoolBrief(SchoolIdentity):
    official_identifier: str
    state: SchoolState

    name: str

    collection_count: int

    class Config:
        orm_mode = True


class SchoolDetail(SchoolBrief):
    country: CountryDetail
    info: Optional[SchoolInfo]

    student_domain: Optional[AnyHttpUrl]
    teacher_domain: Optional[AnyHttpUrl]

    class Config:
        orm_mode = True


class SchoolCreateIn(BaseModel):
    name: str
    country_code: constr(min_length=3, max_length=3)
    official_identifier: Optional[str]
    info: SchoolInfo
    student_domain: Optional[AnyHttpUrl]
    teacher_domain: Optional[AnyHttpUrl]


# Note can't change the country code or official identifier
class SchoolUpdateIn(BaseModel):
    name: Optional[str]
    info: Optional[Any]
    student_domain: Optional[AnyHttpUrl]
    teacher_domain: Optional[AnyHttpUrl]