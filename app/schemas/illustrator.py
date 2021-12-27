from typing import Optional, Any

from pydantic import BaseModel


class IllustratorCreateIn(BaseModel):
    full_name: str
    info: Optional[Any]


class IllustratorBrief(BaseModel):
    id: str
    full_name: str
    info: Optional[Any]

    class Config:
        orm_mode = True

