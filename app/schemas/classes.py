import enum
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.booklist import ListType
from app.schemas.pagination import PaginatedResponse
from app.schemas.school import SchoolBrief
from app.schemas.user import UserIdentity
from app.schemas.work import WorkBrief


class ClassIdentifier(BaseModel):
    id: UUID = Field(None, description="Class Identifier (Wriveted UUID)")
    school_id: UUID = Field(None, description="School Identifier (Wriveted UUID)")

    class Config:
        orm_mode = True


class ClassBrief(ClassIdentifier):
    name: str = Field(None, description="Class name")


class ClassBriefWithJoiningCode(ClassIdentifier):
    code: str = Field(None, description="Joining code")
    note: Optional[str] = Field(None, description="Note about this class")


class ClassDetail(ClassBriefWithJoiningCode):
    admins: list[UserIdentity]
    members: list[UserIdentity]


class ClassListResponse(PaginatedResponse):
    data: list[ClassBrief]


class ClassCreateIn(BaseModel):
    school_id: UUID = Field(None, description="School Identifier")
    name: str = Field(None, description="Class name")


class ClassMemberUpdateType(str, enum.Enum):
    ADD = "add"
    REMOVE = "remove"
    #UPDATE = "update"


class ClassMemberUpdateIn(BaseModel):
    action: ClassMemberUpdateType
    user_id: UUID


# Note we don't allow changing the joining code (should we?)
class ClassUpdateIn(BaseModel):
    name: Optional[str]
    note: Optional[str] = Field(None, description="Note about this class")

    members: Optional[list[ClassMemberUpdateIn]]
    admins: Optional[list[ClassMemberUpdateIn]]