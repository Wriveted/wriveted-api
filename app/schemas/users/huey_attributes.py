from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class HueyAttributes(BaseModel):
    birthdate: str | None
    reading_ability: Any | None
    last_visited: str | None
