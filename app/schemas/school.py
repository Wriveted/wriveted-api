from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, StringConstraints
from typing_extensions import Annotated

from app.models import SchoolState
from app.models.school import SchoolBookbotType
from app.schemas.collection import CollectionBrief
from app.schemas.country import CountryDetail

# pylint: disable=unused-import
from app.schemas.school_identity import SchoolIdentity
from app.schemas.users import UserBrief


class SchoolLocation(BaseModel):
    suburb: Optional[str] = None
    state: str
    postcode: str
    geolocation: Optional[str] = None
    lat: Optional[str] = None
    long: Optional[str] = None


class SchoolInfo(BaseModel):
    location: SchoolLocation
    type: Optional[str] = None
    sector: Optional[str] = None
    URL: Optional[str] = None
    status: Optional[str] = None
    age_id: Optional[str] = None
    experiments: Optional[dict[str, bool]] = None


class SchoolBrief(SchoolIdentity):
    name: str
    state: SchoolState | None = None
    collection: CollectionBrief | None = None


class SchoolSelectorOption(SchoolBrief):
    info: SchoolInfo
    admins: list[UserBrief]


class SchoolBookbotInfo(BaseModel):
    wriveted_identifier: UUID
    name: str
    state: SchoolState
    bookbot_type: SchoolBookbotType
    model_config = ConfigDict(from_attributes=True)


class BookListID(BaseModel):
    id: UUID
    name: str
    model_config = ConfigDict(from_attributes=True)


class SchoolDetail(SchoolBrief):
    country: CountryDetail
    info: Optional[SchoolInfo] = None

    admins: list[UserBrief]
    lms_type: str
    bookbot_type: SchoolBookbotType

    created_at: datetime
    updated_at: datetime

    student_domain: Optional[AnyHttpUrl] = None
    teacher_domain: Optional[AnyHttpUrl] = None

    booklists: list[BookListID]


class SchoolCreateIn(BaseModel):
    name: str
    country_code: Annotated[str, StringConstraints(min_length=3, max_length=3)]
    official_identifier: Optional[str] = None
    bookbot_type: Optional[SchoolBookbotType] = None
    lms_type: Optional[str] = None
    info: SchoolInfo
    student_domain: Optional[AnyHttpUrl] = None
    teacher_domain: Optional[AnyHttpUrl] = None


# Note can't change the country code or official identifier
class SchoolUpdateIn(BaseModel):
    name: Optional[str] = None
    info: Optional[Any] = None
    student_domain: Optional[AnyHttpUrl] = None
    teacher_domain: Optional[AnyHttpUrl] = None


class SchoolPatchOptions(BaseModel):
    status: Optional[SchoolState] = None
    bookbot_type: Optional[SchoolBookbotType] = None
    lms_type: Optional[str] = None
    name: Optional[str] = None
    info: Optional[Any] = None
    student_domain: Optional[AnyHttpUrl] = None
    teacher_domain: Optional[AnyHttpUrl] = None
