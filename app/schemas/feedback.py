from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, StringConstraints
from typing_extensions import Annotated

from app.schemas.sendgrid import SendGridEmailData


class SendEmailPayload(BaseModel):
    email_data: SendGridEmailData
    user_id: str | None = None
    service_account_id: str | None = None


class SendSmsPayload(BaseModel):
    to: str | list[str]
    body: str
    shorten_urls: bool = False


class ReadingLogEventDetail(BaseModel):
    """
    For supporters, this is the data that is sent to the client to display a reading log feedback form.
    """

    reader_name: str
    supporter_nickname: str

    book_title: str
    cover_url: str | None = None

    emoji: str
    descriptor: str
    timestamp: datetime
    finished: bool
    stopped: bool


class ReadingLogEventFeedback(BaseModel):
    event_id: str
    comment: Annotated[str, StringConstraints(min_length=5, max_length=140)]
    gif_url: AnyHttpUrl
