from pydantic import BaseModel, EmailStr, validator, parse_obj_as
from app.config import get_settings
from sendgrid import SendGridAPIClient
from json import loads

config = get_settings()


class CustomField(BaseModel):
    name: str
    value: int | str | None
    id: str | None


def get_sendgrid_custom_fields() -> list[CustomField]:
    """
    Produces a list of the custom field objects currently on the SendGrid account
    """
    sg = SendGridAPIClient(config.SENDGRID_API_KEY)
    fields_raw = sg.client.marketing.field_definitions.get()
    fields_obj = loads(fields_raw.body)["custom_fields"]
    return parse_obj_as(list[CustomField], fields_obj)


class ContactData(BaseModel):
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
    custom_fields: dict[str, int | str] | None

    @validator("custom_fields", pre=True)
    def validate_custom_fields(cls, value):
        supplied_fields: list[CustomField] = parse_obj_as(list[CustomField], value)
        output: dict[str, int | str] = {}
        # enrich the 'named' fields with their equivalent ids, provided they exist
        current_fields = get_sendgrid_custom_fields()
        for supplied_field in supplied_fields:
            id = next(
                (
                    field.id
                    for field in current_fields
                    if field.name == supplied_field.name
                ),
                None,
            )
            if id:
                output[id] = supplied_field.value
            else:
                raise ValueError(
                    f"No custom field exists with the name {supplied_field.name}."
                )

        return output


class EmailData(BaseModel):
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
