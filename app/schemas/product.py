from __future__ import annotations

from pydantic import BaseModel


class ProductBrief(BaseModel):
    id: str  # a stripe "price" id
    name: str

    class Config:
        orm_mode = True


class ProductCreateIn(ProductBrief):
    class Config:
        orm_mode = False


class ProductUpdateIn(ProductBrief):
    class Config:
        orm_mode = False
