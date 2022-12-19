from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel

from app.schemas.product import ProductBrief


class SubscriptionBrief(BaseModel):
    id: str
    type: Literal["family"]
    provider: Literal["stripe"]
    is_active: bool
    expiration: datetime | None
    product: ProductBrief

    class Config:
        orm_mode = True


class SubscriptionDetail(SubscriptionBrief):
    stripe_customer_id: str
    created_at: datetime
    updated_at: datetime
    info: Optional[Any]


class SubscriptionCreateIn(BaseModel):
    id: str
    stripe_customer_id: str
    parent_id: str | None
    product_id: str
    is_active: bool | None
    info: dict | None
    latest_checkout_session_id: str | None
    expiration: datetime | None


class SubscriptionUpdateIn(BaseModel):
    product_id: str | None
    is_active: bool | None
    info: dict | None
    latest_checkout_session_id: str | None
    expiration: datetime | None
