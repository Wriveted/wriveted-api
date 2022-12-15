from __future__ import annotations

from pydantic import BaseModel


class ProductBrief(BaseModel):
    id: str  # a stripe "price" id
    name: str
