from pydantic import BaseModel, EmailStr, validator


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
