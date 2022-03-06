from enum import Enum
from typing import Optional
from pydantic import BaseModel

class GenreSource(Enum):
    BISAC = "BISAC"
    BIC   = "BIC"
    THEMA = "THEMA"
    LOCSH = "LOCSH"
    HUMAN = "HUMAN"
    OTHER = "OTHER"

class Genre(BaseModel):
    name: str
    source: GenreSource

    class Config:
        orm_mode = True