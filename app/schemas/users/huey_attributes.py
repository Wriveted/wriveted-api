from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.recommendations import ReadingAbilityKey


class HueyAttributes(BaseModel):
    birthdate: datetime | None
    reading_ability: list[ReadingAbilityKey] | None
    last_visited: datetime | None
