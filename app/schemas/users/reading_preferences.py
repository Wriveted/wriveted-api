from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.recommendations import ReadingAbilityKey


class ReadingPreferences(BaseModel):
    birthdate: date | None
    reading_ability: ReadingAbilityKey | None
    last_visited: datetime | None
