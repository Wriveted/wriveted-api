from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class ReadingLogEventDetail(BaseModel):
    """
    For pseudousers, this is the data that is sent to the client to display a reading log feedback form.
    """

    reader_name: str

    book_title: str
    cover_url: str

    emoji: str
    descriptor: str
    timestamp: datetime
    finished: bool
    stopped: bool


class ReaderFeedbackOtpData(BaseModel):
    """
    Data concering a friend/family recipient of a reading log alert, containing the information
    to be encoded to allow them to provide feedback on the reading log, without having an account and/or logging in.
    """

    nickname: str | None
    email: str | None
    phone: str | None
    event_id: UUID | None


class ReadingLogEventFeedback(BaseModel):
    emoji: str
    comment: str
    gif_url: str


class HasReaderFeedbackOtp(BaseModel):
    otp: ReaderFeedbackOtpData
