import enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.schemas.school import SchoolBrief
from app.schemas.user import UserBrief
from app.schemas.work import WorkBrief


class BookListBase(BaseModel):
    id: int
    name: str
    book_count: int
    created_at: datetime

    user: Optional[UserBrief]
    school: Optional[SchoolBrief]

    works: list[WorkBrief]

    class Config:
        orm_mode = True
