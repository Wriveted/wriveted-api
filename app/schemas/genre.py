from pydantic import BaseModel

class Genre(BaseModel):
    id: str
    name: str

    class Config:
        orm_mode = True