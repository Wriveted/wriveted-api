from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict


class Hue(BaseModel):
    id: Annotated[str, BeforeValidator(str)]
    name: str
    key: str

    model_config = ConfigDict(from_attributes=True)


class HueCreateIn(BaseModel):
    id: Annotated[str, BeforeValidator(str)]
    name: str
    key: str
