from pydantic import BaseModel, ConfigDict


class Hue(BaseModel):
    id: str
    name: str
    key: str
    model_config = ConfigDict(from_attributes=True)


class HueCreateIn(BaseModel):
    id: str
    name: str
    key: str
