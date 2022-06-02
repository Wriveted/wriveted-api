import enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.pagination import PaginatedResponse
from app.schemas.user import UserIdentity


class ClassGroupIdentifier(BaseModel):
    id: UUID = Field(None, description="Class Identifier (Wriveted UUID)")
    school_id: UUID = Field(None, description="School Identifier (Wriveted UUID)")

    class Config:
        orm_mode = True


class ClassGroupBrief(ClassGroupIdentifier):
    name: str = Field(None, description="Class name")


class ClassGroupBriefWithJoiningCode(ClassGroupIdentifier):
    code: str = Field(None, description="Joining code")
    note: Optional[str] = Field(None, description="Note about this class")


class ClassGroupDetail(ClassGroupBriefWithJoiningCode):
    admins: list[UserIdentity]
    members: list[UserIdentity]


class ClassGroupListResponse(PaginatedResponse):
    data: list[ClassGroupBrief]


class ClassGroupCreateIn(BaseModel):
    school_id: UUID = Field(None, description="School Identifier")
    name: str = Field(None, description="Class name")


class ClassGroupMemberUpdateType(str, enum.Enum):
    ADD = "add"
    REMOVE = "remove"
    # UPDATE = "update"


class ClassGroupMemberUpdateIn(BaseModel):
    action: ClassGroupMemberUpdateType
    user_id: UUID


# Note we don't allow changing the joining code (should we?)
class ClassGroupUpdateIn(BaseModel):
    name: Optional[str]
    note: Optional[str] = Field(None, description="Note about this class")

    members: Optional[list[ClassGroupMemberUpdateIn]]
    admins: Optional[list[ClassGroupMemberUpdateIn]]
