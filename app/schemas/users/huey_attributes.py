from __future__ import annotations

from pydantic import BaseModel, StringConstraints
from typing_extensions import Annotated

from app.schemas.recommendations import HueKeys, ReadingAbilityKey


class HueyAttributes(BaseModel):
    birthdate: Annotated[
        str,
        StringConstraints(
            pattern=r"(\d{4})-(\d{2})-(\d{2})( (\d{2}):(\d{2}):(\d{2}))?"
        ),
    ] | None = None
    last_visited: Annotated[
        str,
        StringConstraints(
            pattern=r"(\d{4})-(\d{2})-(\d{2})( (\d{2}):(\d{2}):(\d{2}))?"
        ),
    ] | None = None

    age: int | None = None
    reading_ability: list[ReadingAbilityKey] | None = None
    hues: list[HueKeys] | None = None

    goals: list[str] | None = None
    genres: list[str] | None = None
    characters: list[str] | None = None

    parent_nickname: str | None = None
