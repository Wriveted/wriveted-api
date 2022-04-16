import enum
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from app.models.booklist import ListType
from app.schemas.school import SchoolBrief
from app.schemas.user import UserBrief
from app.schemas.work import WorkBrief


class BookListBase(BaseModel):
    name: str
    type: ListType



class BookListCreateIn(BookListBase):
    type: ListType
    works: Optional[list[WorkBrief]]


class BookListBrief(BookListBase):
    id: UUID
    created_at: datetime
    book_count: int
    user: Optional[UserBrief]
    school: Optional[SchoolBrief]

    class Config:
        orm_mode = True


class BookListDetail(BookListBrief):
    works: list[WorkBrief]