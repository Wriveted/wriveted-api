from datetime import datetime
from uuid import UUID
from pydantic import AnyHttpUrl, BaseModel, constr

from app.schemas.sendgrid import SendGridEmailData


class SendEmailPayload(BaseModel):
    email_data: SendGridEmailData
    user_id: str | None
    service_account_id: str | None


class SendSmsPayload(BaseModel):
    to: str | list[str]
    body: str
    shorten_urls: bool = False


class ReadingLogEventDetail(BaseModel):
    """
    For supporters, this is the data that is sent to the client to display a reading log feedback form.
    """

    reader_name: str

    book_title: str
    cover_url: str

    emoji: str
    descriptor: str
    timestamp: datetime
    finished: bool
    stopped: bool


class ReadingLogEventFeedback(BaseModel):
    event_id: UUID
    emoji: constr(min_length=1, max_length=1)
    comment: constr(min_length=5, max_length=100)
    gif_url: AnyHttpUrl
