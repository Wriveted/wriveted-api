from typing import Optional
from pydantic import BaseModel

class Genre(BaseModel):
    name: str
    bisac_code: Optional[str]

    class Config:
        orm_mode = True