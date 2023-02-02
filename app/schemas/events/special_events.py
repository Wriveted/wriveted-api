from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ReadingLogEvent(BaseModel):
    collection_item_id: int
    collection_id: UUID
    descriptor: str
    emoji: str
    timestamp: datetime
    finished: bool = False
