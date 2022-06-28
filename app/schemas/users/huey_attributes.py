from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, constr

from app.schemas.recommendations import ReadingAbilityKey


class HueyAttributes(BaseModel):
    birthdate: constr(
        regex=r"(\d{4})-(\d{2})-(\d{2})( (\d{2}):(\d{2}):(\d{2}))?"
    ) | None
    reading_ability: list[ReadingAbilityKey] | None
    last_visited: constr(
        regex=r"(\d{4})-(\d{2})-(\d{2})( (\d{2}):(\d{2}):(\d{2}))?"
    ) | None
