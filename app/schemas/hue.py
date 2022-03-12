from pydantic import BaseModel


class Hue(BaseModel):
    id: str
    name: str
    key: str

    class Config:
        orm_mode = True


class HueCreateIn(BaseModel):
    id: str
    name: str
    key: str
