from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Extra


class ShopifyEmailConsentSettings(BaseModel):
    state: str | None
    opt_in_level: str | None
    consent_updated_at: datetime | None


class ShopifyCustomerAddress(BaseModel):
    id: int
    customer_id: int
    first_name: str | None
    last_name: str | None
    company: str | None
    address1: str | None
    address2: str | None
    city: str | None
    province: str | None
    country: str | None
    zip: str | None
    phone: str | None
    name: str | None
    province_code: str | None
    country_code: str | None
    country_name: str | None
    default: bool | None


class ShopifyCustomer(BaseModel):
    id: int
    email: EmailStr | None
    accepts_marketing: bool | None
    created_at: datetime | None
    updated_at: datetime | None
    first_name: str | None
    last_name: str | None
    orders_count: int | None
    state: str | None
    total_spent: str | None
    last_order_id: int | None
    note: Any | None
    verified_email: bool | None
    multipass_identifier: Any | None
    tax_exempt: bool | None
    tags: str | None
    last_order_name: str | None
    currency: str | None
    phone: str | None
    accepts_marketing_updated_at: datetime | None
    marketing_opt_in_level: str | None
    email_marketing_consent: ShopifyEmailConsentSettings | None
    sms_marketing_consent: str | None
    admin_graphql_api_id: str | None
    default_address: ShopifyCustomerAddress | None


class ShopifyEventRoot(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime
    customer: ShopifyCustomer | None
    total_price: str | None

    class Config:
        extra = Extra.allow
