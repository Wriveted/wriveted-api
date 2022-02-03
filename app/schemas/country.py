from pydantic import BaseModel


class CountryDetail(BaseModel):
    id: str
    name: str

    class Config:
        orm_mode = True
