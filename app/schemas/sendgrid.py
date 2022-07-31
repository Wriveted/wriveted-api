from datetime import datetime
from pydantic import BaseModel, EmailStr, validator
from app.config import get_settings

config = get_settings()


class SendGridCustomField(BaseModel):
    name: str
    value: int | datetime | str | None
    id: str | None


class SendGridContactData(BaseModel):
    email: EmailStr
    first_name: str | None
    last_name: str | None
    address_line_1: str | None
    address_line_2: str | None
    city: str | None
    state_province_region: str | None
    postal_code: str | None
    country: str | None
    phone_number: str | None
    whatsapp: str | None
    line: str | None
    facebook: str | None
    unique_name: str | None


class CustomSendGridContactData(SendGridContactData):
    custom_fields: dict[str, int | datetime | str] | None


class SendGridEmailData(BaseModel):
    from_email: EmailStr = "hello@hueybooks.com"
    from_name: str | None
    to_emails: list[EmailStr]
    subject: str | None
    template_id: str | None
    template_data: dict = {}

    @validator("template_data", always=True)
    def validate_template_data(cls, value, values):
        if value and not values.get("template_id"):
            raise ValueError("Must provide template id if providing template data.")
        return value
