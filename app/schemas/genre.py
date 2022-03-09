from pydantic import BaseModel
from app.models.genre import GenreSource

class Genre(BaseModel):
    name: str
    source: GenreSource

    class Config:
        orm_mode = True

    def __eq__(self, other):
        return self.name==other.name\
            and self.source==other.source

    def __hash__(self):
        return hash(('name', self.name,
            'source', self.source))