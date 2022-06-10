from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.db_job import JobStatus, JobType


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
