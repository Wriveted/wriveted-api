from pydantic import BaseModel, ConfigDict


class CountryDetail(BaseModel):
    id: str
    name: str
    model_config = ConfigDict(from_attributes=True)
