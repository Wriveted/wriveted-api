from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.recommendations import ReadingAbilityKey


class HueyAttributes(BaseModel):
    birthdate: str | None
    reading_ability: Any | None
    last_visited: str | None
