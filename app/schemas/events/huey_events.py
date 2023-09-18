from pydantic import BaseModel


class HueyEventsSharedInfo(BaseModel):
    chatbot: str | None = None
    experiments: dict[str, bool] | None = None
    school_name: str | None = None
    distinct_id: str | None = None


class HueyBookReviewedInfo(HueyEventsSharedInfo):
    isbn: str | None = None
    read: bool
    image: str | None = None
    liked: bool
    title: str | None = None
    author: str | None = None
