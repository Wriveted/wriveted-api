from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class SchoolWrivetedIdentity(BaseModel):
    wriveted_identifier: UUID
    name: str

    class Config:
        orm_mode = True


class SchoolIdentity(SchoolWrivetedIdentity):
    official_identifier: Optional[str]
    country_code: str
