from typing import Any

from pydantic import BaseModel

from app.schemas.author import ContributorBase


class IllustratorCreateIn(ContributorBase):
    info: Any | None


class IllustratorBrief(ContributorBase):
    id: int
    info: Any | None

    class Config:
        orm_mode = True
