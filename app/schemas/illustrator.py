from typing import Any

from pydantic import BaseModel


class IllustratorCreateIn(BaseModel):
    first_name: str | None
    last_name: str
    info: Any | None


class IllustratorBrief(BaseModel):
    id: str
    first_name: str | None
    last_name: str
    info: Any | None

    class Config:
        orm_mode = True
