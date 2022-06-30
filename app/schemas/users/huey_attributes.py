from __future__ import annotations
from pydantic import BaseModel, constr


class HueyAttributes(BaseModel):
    birthdate: constr(
        regex=r"(\d{4})-(\d{2})-(\d{2})( (\d{2}):(\d{2}):(\d{2}))?"
    ) | None
    reading_ability: list[ReadingAbilityKey] | None
    last_visited: constr(
        regex=r"(\d{4})-(\d{2})-(\d{2})( (\d{2}):(\d{2}):(\d{2}))?"
    ) | None
