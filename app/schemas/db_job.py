from xmlrpc.client import DateTime
from pydantic import BaseModel

from app.models.db_job import JobStatus
from app.models.db_job import JobType
from typing import Optional, Any

class DbJob(BaseModel):
    id: str
    status: JobStatus
    type: JobType
    summary: Optional[Any]
    created_timestamp: DateTime
    started_timestamp: DateTime
    ended_timestamp: DateTime

    class Config:
        orm_mode = True