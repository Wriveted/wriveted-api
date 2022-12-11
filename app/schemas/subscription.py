from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel


class SubscriptionBrief(BaseModel):
    id: str
    type: Literal["family"]
    provider: Literal["stripe"]
    is_active: bool


class SubscriptionDetail(SubscriptionBrief):
    stripe_customer_id: str
    created_at: datetime
    updated_at: datetime
    info: Optional[Any]
