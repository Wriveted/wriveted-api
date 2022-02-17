from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.db_job import JobStatus
from app.models.db_job import JobType
from typing import Optional, Any


class DbJob(BaseModel):
    id: UUID
    status: JobStatus
    type: JobType
    summary: Optional[Any]
    created_timestamp: datetime
    started_timestamp: datetime
    ended_timestamp: datetime

    class Config:
        orm_mode = True
