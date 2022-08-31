from __future__ import annotations

from pydantic import BaseModel, constr

from app.schemas.recommendations import ReadingAbilityKey, HueKeys


class HueyAttributes(BaseModel):
    birthdate: constr(
        regex=r"(\d{4})-(\d{2})-(\d{2})( (\d{2}):(\d{2}):(\d{2}))?"
    ) | None
    last_visited: constr(
        regex=r"(\d{4})-(\d{2})-(\d{2})( (\d{2}):(\d{2}):(\d{2}))?"
    ) | None

    age: int | None
    reading_ability: list[ReadingAbilityKey] | None
    hues: list[HueKeys] | None

    goals: list[str] | None
    genres: list[str] | None
    characters: list[str] | None
