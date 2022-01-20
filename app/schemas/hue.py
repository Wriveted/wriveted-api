from pydantic import BaseModel

class Hue(BaseModel):
    id: str
    name: str

    class Config:
        orm_mode = True