from typing import Optional, Any, List

from pydantic import BaseModel, AnyHttpUrl, constr

from app.models import SchoolState


class SchoolIdentity(BaseModel):
    official_identifier: str
    country_code: str


class SchoolBrief(SchoolIdentity):
    official_identifier: str
    state: SchoolState

    name: str

    class Config:
        orm_mode = True


class SchoolDetail(SchoolBrief):

    info: Optional[Any]

    student_domain: Optional[AnyHttpUrl]
    teacher_domain: Optional[AnyHttpUrl]

    class Config:
        orm_mode = True


class SchoolCreateIn(BaseModel):
    name: str
    country_code: constr(min_length=3, max_length=3)
    official_identifier: str
    info: Optional[Any]
    student_domain: Optional[AnyHttpUrl]
    teacher_domain: Optional[AnyHttpUrl]


# Note can't change the country code or official identifier
class SchoolUpdateIn(BaseModel):
    name: Optional[str]
    info: Optional[Any]
    student_domain: Optional[AnyHttpUrl]
    teacher_domain: Optional[AnyHttpUrl]

