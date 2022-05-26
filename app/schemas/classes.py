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
    id: UUID = Field(None, description="Class Identifier")
    name: str = Field(None, description="Class name")


class ClassBrief(ClassIdentifier):

    note: Optional[str] = Field(None, description="Note about this class")


class ClassesResponse(PaginatedResponse):
    data: list[ClassBrief]

