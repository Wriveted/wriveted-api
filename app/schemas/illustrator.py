from typing import Optional, Any

from pydantic import BaseModel


class IllustratorCreateIn(BaseModel):
    first_name: Optional[str]
    last_name: str
    info: Optional[Any]


class IllustratorBrief(BaseModel):
    id: str
    first_name: str
    last_name: str
    info: Optional[Any]

    class Config:
        orm_mode = True
