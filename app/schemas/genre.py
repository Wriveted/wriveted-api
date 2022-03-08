from pydantic import BaseModel
from app.models.genre import GenreSource

class Genre(BaseModel):
    name: str
    source: str

    class Config:
        orm_mode = True