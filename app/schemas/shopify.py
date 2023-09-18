from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr


class ShopifyEmailConsentSettings(BaseModel):
    state: str | None = None
    opt_in_level: str | None = None
    consent_updated_at: datetime | None = None


class ShopifyCustomerAddress(BaseModel):
    id: int
    customer_id: int
    first_name: str | None = None
    last_name: str | None = None
    company: str | None = None
    address1: str | None = None
    address2: str | None = None
    city: str | None = None
    province: str | None = None
    country: str | None = None
    zip: str | None = None
    phone: str | None = None
    name: str | None = None
    province_code: str | None = None
    country_code: str | None = None
    country_name: str | None = None
    default: bool | None = None


class ShopifyCustomer(BaseModel):
    id: int
    email: EmailStr | None = None
    accepts_marketing: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    first_name: str | None = None
    last_name: str | None = None
    orders_count: int | None = None
    state: str | None = None
    total_spent: str | None = None
    last_order_id: int | None = None
    note: Any | None = None
    verified_email: bool | None = None
    multipass_identifier: Any | None = None
    tax_exempt: bool | None = None
    tags: str | None = None
    last_order_name: str | None = None
    currency: str | None = None
    phone: str | None = None
    accepts_marketing_updated_at: datetime | None = None
    marketing_opt_in_level: str | None = None
    email_marketing_consent: ShopifyEmailConsentSettings | None = None
    sms_marketing_consent: str | None = None
    admin_graphql_api_id: str | None = None
    default_address: ShopifyCustomerAddress | None = None


class ShopifyEventRoot(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime
    customer: ShopifyCustomer | None = None
    total_price: str | None = None
    model_config = ConfigDict(extra="allow")
