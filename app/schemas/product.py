from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ProductBrief(BaseModel):
    id: str  # a stripe "price" id
    name: str
    model_config = ConfigDict(from_attributes=True)


class ProductCreateIn(ProductBrief):
    model_config = ConfigDict(from_attributes=False)


class ProductUpdateIn(ProductBrief):
    model_config = ConfigDict(from_attributes=False)
