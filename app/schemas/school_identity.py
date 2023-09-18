from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SchoolWrivetedIdentity(BaseModel):
    wriveted_identifier: UUID
    name: str
    model_config = ConfigDict(from_attributes=True)


class SchoolIdentity(SchoolWrivetedIdentity):
    official_identifier: Optional[str] = None
    country_code: str
