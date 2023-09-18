from typing import Any

from pydantic import ConfigDict

from app.schemas.author import ContributorBase


class IllustratorCreateIn(ContributorBase):
    info: Any | None = None


class IllustratorBrief(ContributorBase):
    id: int
    info: Any | None = None
    model_config = ConfigDict(from_attributes=True)
